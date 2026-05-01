import logging
import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.repository.satellite_repo import SatelliteRepository
from app.utils.math_helpers import (
    tle_epoch_to_datetime,
    classify_confidence,
    extract_constellation,
)

logger = logging.getLogger(__name__)

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
CACHE_TTL_HOURS = 2.0          # re-fetch if data older than 2 hours
REQUEST_TIMEOUT_SEC = 30
MAX_SATELLITES = None          # None = fetch all; set int to limit for testing


def _parse_tle_text(raw_text: str) -> list[dict]:
    """
    Parse raw 3-line TLE text into a list of satellite dicts.
    Handles both 5-digit and 6-digit NORAD IDs.
    Skips malformed entries gracefully.
    """
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
    satellites = []
    i = 0

    while i + 2 < len(lines):
        name_line = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        # Basic validation: TLE lines start with '1 ' and '2 '
        if not (line1.startswith("1 ") and line2.startswith("2 ")):
            i += 1
            continue

        try:
            # NORAD ID from column 3-7 of line1 (supports 6-digit)
            norad_id = int(line1[2:7].strip())
            name = name_line.strip()

            epoch_dt = tle_epoch_to_datetime(line1)
            confidence = classify_confidence(epoch_dt)
            constellation = extract_constellation(name)

            satellites.append({
                "norad_id": norad_id,
                "name": name,
                "tle_line1": line1,
                "tle_line2": line2,
                "epoch": epoch_dt,
                "confidence": confidence,
                "constellation": constellation,
                "fetched_at": datetime.now(timezone.utc),
            })
        except Exception as exc:
            logger.warning(f"Skipping malformed TLE entry at line {i}: {exc}")

        i += 3

    return satellites


def fetch_and_store_tles(db: Session, force: bool = False) -> dict:
    """
    Main entry point for the TLE fetcher.

    - Checks if cached data is fresh enough (< CACHE_TTL_HOURS old)
    - If stale (or force=True), downloads from CelesTrak and upserts to DB
    - Returns a status summary dict

    Args:
        db:    SQLAlchemy session
        force: If True, skip cache check and always fetch

    Returns:
        {
            "fetched": bool,
            "satellite_count": int,
            "source": "cache" | "celestrak",
            "fetched_at": datetime | None,
        }
    """
    repo = SatelliteRepository(db)

    if not force:
        last_fetch = repo.get_last_fetch_time()
        if last_fetch is not None:
            age = datetime.now(timezone.utc) - last_fetch
            if age < timedelta(hours=CACHE_TTL_HOURS):
                count = repo.count()
                logger.info(
                    f"TLE cache is fresh ({age.total_seconds()/3600:.1f}h old). "
                    f"Using {count} cached satellites."
                )
                return {
                    "fetched": False,
                    "satellite_count": count,
                    "source": "cache",
                    "fetched_at": last_fetch,
                }

    logger.info(f"Fetching TLE data from CelesTrak: {CELESTRAK_URL}")

    try:
        response = requests.get(
            CELESTRAK_URL,
            timeout=REQUEST_TIMEOUT_SEC,
            headers={
                "User-Agent": "GroundPassPredictor/1.0 (educational project)",
                "Accept": "text/plain",
            },
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error("CelesTrak request timed out.")
        raise RuntimeError("TLE fetch timed out. CelesTrak may be unavailable.")
    except requests.exceptions.RequestException as exc:
        logger.error(f"CelesTrak fetch failed: {exc}")
        raise RuntimeError(f"TLE fetch failed: {exc}")

    raw_text = response.text

    # Check for CelesTrak's "not updated" message
    if "has not updated" in raw_text.lower() or len(raw_text) < 100:
        logger.warning("CelesTrak returned 'not updated' response — using cached data.")
        count = repo.count()
        return {
            "fetched": False,
            "satellite_count": count,
            "source": "cache (celestrak not updated)",
            "fetched_at": repo.get_last_fetch_time(),
        }

    satellites = _parse_tle_text(raw_text)

    if MAX_SATELLITES:
        satellites = satellites[:MAX_SATELLITES]

    if not satellites:
        raise RuntimeError("TLE parsing returned 0 satellites. Check CelesTrak response.")

    logger.info(f"Parsed {len(satellites)} satellites. Upserting to DB...")
    count = repo.upsert_many(satellites)
    logger.info(f"Upserted {count} satellites.")

    return {
        "fetched": True,
        "satellite_count": count,
        "source": "celestrak",
        "fetched_at": datetime.now(timezone.utc),
    }
