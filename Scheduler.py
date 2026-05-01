import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.repository.pass_repo import PassRepository
from app.repository.station_repo import StationRepository

logger = logging.getLogger(__name__)


def run_scheduler(
    db: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    reset_first: bool = True,
) -> dict:
    """
    Weighted greedy interval scheduling across all 50 ground stations.

    Algorithm (per station):
      1. Fetch all passes for this station in the time window
      2. Sort by LOS time (earliest ending first — classic greedy)
      3. Among ties in LOS, prefer higher quality_score
      4. Greedily select passes that don't overlap with already-scheduled passes
         on this station
      5. Mark selected passes as is_scheduled=True

    Why greedy works here:
      - Each station is an independent resource
      - Greedy earliest-deadline-first is provably optimal for maximizing
        the number of non-overlapping intervals on a single machine
      - Quality weighting means we prefer high-elevation long passes
        when multiple passes have similar LOS times

    Complexity: O(P log P) per station, where P = passes per station
    Total: O(50 × P log P) — sub-second for millions of passes with indexes

    Args:
        db:          SQLAlchemy session
        start_time:  Schedule window start (default: now UTC)
        end_time:    Schedule window end (default: start + 7 days)
        reset_first: Clear previous scheduling flags before running

    Returns:
        Summary dict with scheduling statistics
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc)
    if end_time is None:
        end_time = start_time + timedelta(days=7)

    pass_repo = PassRepository(db)
    stn_repo = StationRepository(db)

    if reset_first:
        logger.info("Resetting previous schedule...")
        pass_repo.reset_schedule()

    stations = stn_repo.get_all()
    total_scheduled = 0
    total_considered = 0
    scheduled_ids = []
    satellites_covered = set()

    for station in stations:
        passes = pass_repo.get_by_station(
            station_id=station.id,
            start=start_time,
            end=end_time,
            min_duration_s=5.0,
        )

        if not passes:
            continue

        # Sort: primary = LOS (earliest first), secondary = quality (highest first)
        sorted_passes = sorted(
            passes,
            key=lambda p: (p.los_time, -p.quality_score)
        )

        total_considered += len(sorted_passes)

        # Greedy selection — track when this station becomes free
        station_free_at = start_time

        for p in sorted_passes:
            # Skip if this station is still busy
            if p.aos_time < station_free_at:
                continue

            # Select this pass
            scheduled_ids.append(p.id)
            station_free_at = p.los_time
            total_scheduled += 1
            satellites_covered.add(p.satellite_id)

        logger.debug(
            f"Station {station.name}: {total_scheduled} scheduled so far"
        )

    # Bulk mark selected passes
    pass_repo.mark_scheduled(scheduled_ids)

    unique_satellites = len(satellites_covered)
    coverage_pct = (unique_satellites / max(total_considered, 1)) * 100

    summary = {
        "window_start": start_time.isoformat(),
        "window_end": end_time.isoformat(),
        "stations_processed": len(stations),
        "passes_considered": total_considered,
        "passes_scheduled": total_scheduled,
        "unique_satellites_covered": unique_satellites,
        "schedule_efficiency_pct": round(
            (total_scheduled / max(total_considered, 1)) * 100, 2
        ),
    }

    logger.info(
        f"Scheduling complete: {total_scheduled} passes scheduled, "
        f"{unique_satellites} unique satellites covered"
    )

    return summary