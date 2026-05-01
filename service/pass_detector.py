import logging
import math
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from repository.satellite_repo import SatelliteRepository
from repository.station_repo import StationRepository
from repository.pass_repo import PassRepository
from service.propagator import propagate_satellite_passes

logger = logging.getLogger(__name__)

# Batch size for DB bulk inserts
INSERT_BATCH_SIZE = 5000

# Batch size for satellite processing (log progress every N satellites)
LOG_EVERY_N = 100


def _extract_mean_motion(tle_line2: str) -> float:
    """
    Extract mean motion (rev/day) from TLE line 2, columns 53-63.
    """
    try:
        return float(tle_line2[52:63].strip())
    except (ValueError, IndexError):
        return 15.0  # default LEO mean motion


def run_pass_detection(
    db: Session,
    start_time: Optional[datetime] = None,
    satellite_limit: Optional[int] = None,
    clear_existing: bool = False,
) -> dict:
    """
    Orchestrate full pass detection for all satellites over all ground stations.

    Args:
        db:               SQLAlchemy session
        start_time:       Propagation start (default: now UTC)
        satellite_limit:  Process only first N satellites (for testing)
        clear_existing:   If True, wipe pass table before running

    Returns:
        Summary dict with counts and timing
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc)

    sat_repo = SatelliteRepository(db)
    stn_repo = StationRepository(db)
    pass_repo = PassRepository(db)

    if clear_existing:
        logger.info("Clearing existing pass events...")
        pass_repo.delete_all()

    satellites = sat_repo.get_all()
    stations = stn_repo.get_all()

    if satellite_limit:
        satellites = satellites[:satellite_limit]

    # Convert station ORM objects to plain dicts once — avoids repeated attribute access
    station_dicts = [
        {
            "id": s.id,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "elevation_m": s.elevation_m,
            "min_elevation_deg": s.min_elevation_deg,
        }
        for s in stations
    ]

    logger.info(
        f"Starting pass detection: {len(satellites)} satellites × "
        f"{len(station_dicts)} stations | window: {start_time} + 7 days"
    )

    wall_start = datetime.now(timezone.utc)
    total_passes = 0
    failed_satellites = 0
    pending_batch = []

    for idx, sat in enumerate(satellites):
        if idx > 0 and idx % LOG_EVERY_N == 0:
            elapsed = (datetime.now(timezone.utc) - wall_start).total_seconds()
            logger.info(
                f"Progress: {idx}/{len(satellites)} satellites | "
                f"{total_passes} passes found | {elapsed:.1f}s elapsed"
            )

        try:
            mean_motion = _extract_mean_motion(sat.tle_line2)

            passes = propagate_satellite_passes(
                tle_line1=sat.tle_line1,
                tle_line2=sat.tle_line2,
                satellite_db_id=sat.id,
                mean_motion_rev_per_day=mean_motion,
                stations=station_dicts,
                start_time=start_time,
            )

            pending_batch.extend(passes)
            total_passes += len(passes)

            # Flush to DB in batches to control memory
            if len(pending_batch) >= INSERT_BATCH_SIZE:
                pass_repo.bulk_insert(pending_batch)
                pending_batch.clear()

        except Exception as exc:
            logger.warning(f"Failed to propagate satellite {sat.norad_id} ({sat.name}): {exc}")
            failed_satellites += 1
            continue

    # Final flush
    if pending_batch:
        pass_repo.bulk_insert(pending_batch)

    elapsed_total = (datetime.now(timezone.utc) - wall_start).total_seconds()

    summary = {
        "satellites_processed": len(satellites) - failed_satellites,
        "satellites_failed": failed_satellites,
        "stations_count": len(station_dicts),
        "total_passes": total_passes,
        "elapsed_seconds": round(elapsed_total, 2),
        "passes_per_second": round(total_passes / max(elapsed_total, 1), 1),
        "start_time": start_time.isoformat(),
    }

    logger.info(
        f"Pass detection complete: {total_passes} passes in {elapsed_total:.1f}s "
        f"({summary['passes_per_second']} passes/s)"
    )
    return summary
