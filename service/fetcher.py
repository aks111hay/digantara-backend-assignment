import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from requests.adapters import HTTPAdapter
from logger import LoggedRetry, get_logger
from config import fetch_const

def _build_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = LoggedRetry(      # ← changed
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

from repository.satellite_repo import SatelliteRepository
from utils.math_helpers import (
    tle_epoch_to_datetime,
    classify_confidence,
    extract_constellation,
)

logger = get_logger()




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
            if age < timedelta(hours=fetch_const.CACHE_TTL_HOURS):
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
        else:
            logger.error("last fetch is None")

    logger.info(f"Fetching TLE data from CelesTrak: {fetch_const.CELESTRAK_URL}")

    try:
        session = _build_session()
        response = session.get(fetch_const.CELESTRAK_URL, timeout=fetch_const.REQUEST_TIMEOUT_SEC, headers={...})
        response.raise_for_status()
        logger.info(f"CelesTrak fetch succeeded | status={response.status_code}")
    except requests.exceptions.RetryError as e:
        logger.error(f"All retries exhausted | {e}")
        raise RuntimeError("TLE fetch failed after all retries.")
    except requests.exceptions.RequestException as e:
        logger.error(f"CelesTrak fetch failed | {e}")
        raise RuntimeError(f"TLE fetch failed: {e}")

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

    if fetch_const.MAX_SATELLITES:
        satellites = satellites[:fetch_const.MAX_SATELLITES]

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
