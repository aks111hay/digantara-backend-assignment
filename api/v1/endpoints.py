import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from db.base import get_db
from models.schemas import (
    SatelliteResponse, GroundStationResponse, PassEventResponse,
    FetchResult, PropagationResult, SchedulerResult, NetworkStats,
)
from repository.satellite_repo import SatelliteRepository
from repository.station_repo import StationRepository
from repository.pass_repo import PassRepository
from service.fetcher import fetch_and_store_tles
from service.pass_detector import run_pass_detection
from service.scheduler import run_scheduler

logger = logging.getLogger(__name__)
router = APIRouter()


# ── TLE / Data Ingestion ───────────────────────────────────────────────────────

@router.post("/fetch-tles", response_model=FetchResult, tags=["Data Ingestion"])
def fetch_tles(
    force: bool = Query(False, description="Force re-fetch even if cache is fresh"),
    db: Session = Depends(get_db),
):
    """
    Download TLE data from CelesTrak and store in DB.
    Respects 2-hour cache — use force=true to override.
    """
    try:
        result = fetch_and_store_tles(db, force=force)
        result["message"] = (
            f"Fetched {result['satellite_count']} satellites from {result['source']}"
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ── Propagation ────────────────────────────────────────────────────────────────

@router.post("/propagate", response_model=PropagationResult, tags=["Propagation"])
def propagate_passes(
    satellite_limit: Optional[int] = Query(
        None, description="Limit satellites for testing (e.g. 100)"
    ),
    clear_existing: bool = Query(True, description="Clear existing passes before running"),
    db: Session = Depends(get_db),
):
    """
    Run SGP4 propagation for all satellites over all 50 ground stations for 7 days.
    Stores all pass events (AOS, LOS, max elevation, quality score) in DB.

    ⚠️ Full run (~6000 satellites) takes several minutes. Use satellite_limit for testing.
    """
    sat_count = SatelliteRepository(db).count()
    if sat_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No satellites in DB. Call /fetch-tles first."
        )

    result = run_pass_detection(
        db=db,
        satellite_limit=satellite_limit,
        clear_existing=clear_existing,
    )
    return result


# ── Scheduling ─────────────────────────────────────────────────────────────────

@router.post("/schedule", response_model=SchedulerResult, tags=["Scheduling"])
def schedule_passes(
    db: Session = Depends(get_db),
):
    """
    Run greedy weighted interval scheduling across all 50 ground stations.
    Maximises unique satellites tracked while respecting one-antenna-one-satellite constraint.
    Marks selected passes with is_scheduled=True.
    """
    pass_count = PassRepository(db).count_total()
    if pass_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No passes in DB. Call /propagate first."
        )

    result = run_scheduler(db=db)
    return result


# ── Satellites ─────────────────────────────────────────────────────────────────

@router.get("/satellites", response_model=List[SatelliteResponse], tags=["Satellites"])
def list_satellites(
    constellation: Optional[str] = Query(None, description="Filter by constellation e.g. STARLINK"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """List all satellites. Optionally filter by constellation."""
    repo = SatelliteRepository(db)
    if constellation:
        sats = repo.get_by_constellation(constellation)
    else:
        sats = repo.get_all()
    return sats[offset: offset + limit]


@router.get("/satellites/{norad_id}", response_model=SatelliteResponse, tags=["Satellites"])
def get_satellite(norad_id: int, db: Session = Depends(get_db)):
    """Get a satellite by NORAD ID."""
    sat = SatelliteRepository(db).get_by_norad_id(norad_id)
    if not sat:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id} not found")
    return sat


@router.get("/satellites/{norad_id}/passes", response_model=List[PassEventResponse], tags=["Satellites"])
def get_satellite_passes(
    norad_id: int,
    days: int = Query(7, le=7, ge=1),
    db: Session = Depends(get_db),
):
    """Get all upcoming passes for a specific satellite across all stations."""
    sat = SatelliteRepository(db).get_by_norad_id(norad_id)
    if not sat:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id} not found")

    now = datetime.now(timezone.utc)
    passes = PassRepository(db).get_by_satellite(
        satellite_id=sat.id,
        start=now,
        end=now + timedelta(days=days),
    )
    return passes


# ── Ground Stations ────────────────────────────────────────────────────────────

@router.get("/stations", response_model=List[GroundStationResponse], tags=["Ground Stations"])
def list_stations(db: Session = Depends(get_db)):
    """List all 50 ground stations."""
    return StationRepository(db).get_all()


@router.get("/stations/{station_id}/passes", response_model=List[PassEventResponse], tags=["Ground Stations"])
def get_station_passes(
    station_id: int,
    hours: int = Query(24, le=168, ge=1, description="Look-ahead window in hours"),
    min_elevation: float = Query(5.0, ge=0.0, le=90.0),
    scheduled_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Get passes for a specific ground station.
    Filter by time window, minimum elevation, and scheduled status.
    Uses composite index for sub-second response.
    """
    station = StationRepository(db).get_by_id(station_id)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")

    now = datetime.now(timezone.utc)
    pass_repo = PassRepository(db)

    if scheduled_only:
        passes = pass_repo.get_scheduled(
            start=now,
            end=now + timedelta(hours=hours),
        )
        passes = [p for p in passes if p.station_id == station_id]
    else:
        passes = pass_repo.get_by_station(
            station_id=station_id,
            start=now,
            end=now + timedelta(hours=hours),
            min_elevation_deg=min_elevation,
        )

    return passes


# ── Passes ─────────────────────────────────────────────────────────────────────

@router.get("/passes", response_model=List[PassEventResponse], tags=["Passes"])
def list_passes(
    station_id: Optional[int] = Query(None),
    satellite_id: Optional[int] = Query(None),
    scheduled_only: bool = Query(False),
    hours: int = Query(24, le=168),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """
    Flexible pass query endpoint.
    Filter by station, satellite, scheduled status, time window.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours)
    pass_repo = PassRepository(db)

    if station_id:
        passes = pass_repo.get_by_station(station_id=station_id, start=now, end=end)
    elif satellite_id:
        passes = pass_repo.get_by_satellite(satellite_id=satellite_id, start=now, end=end)
    elif scheduled_only:
        passes = pass_repo.get_scheduled(start=now, end=end)
    else:
        # Default: next 24h across all stations
        passes = pass_repo.get_scheduled(start=now, end=end)

    if scheduled_only:
        passes = [p for p in passes if p.is_scheduled]

    return passes[:limit]


# ── Network Analytics ──────────────────────────────────────────────────────────

@router.get("/network/stats", response_model=NetworkStats, tags=["Analytics"])
def network_stats(db: Session = Depends(get_db)):
    """
    Network-wide statistics:
    - Total satellites, stations, passes
    - Scheduled passes and unique satellites covered
    - Busiest stations by pass count
    """
    sat_repo = SatelliteRepository(db)
    pass_repo = PassRepository(db)
    stn_repo = StationRepository(db)

    return {
        "total_satellites": sat_repo.count(),
        "total_stations": stn_repo.count(),
        "total_passes": pass_repo.count_total(),
        "scheduled_passes": pass_repo.count_scheduled(),
        "unique_satellites_covered": pass_repo.unique_satellites_tracked(),
        "busiest_stations": pass_repo.busiest_stations(limit=10),
    }


@router.get("/network/schedule", response_model=List[PassEventResponse], tags=["Analytics"])
def full_schedule(
    hours: int = Query(24, le=168),
    db: Session = Depends(get_db),
):
    """Return the full optimized schedule across all stations for a time window."""
    now = datetime.now(timezone.utc)
    return PassRepository(db).get_scheduled(
        start=now,
        end=now + timedelta(hours=hours),
    )
