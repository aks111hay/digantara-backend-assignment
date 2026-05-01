from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


# ── Satellite schemas ──────────────────────────────────────────────────────────

class SatelliteBase(BaseModel):
    norad_id: int
    name: str
    constellation: Optional[str] = None
    confidence: str

class SatelliteResponse(SatelliteBase):
    id: int
    epoch: Optional[datetime] = None
    fetched_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Ground Station schemas ─────────────────────────────────────────────────────

class GroundStationResponse(BaseModel):
    id: int
    name: str
    country: str
    latitude: float
    longitude: float
    elevation_m: float
    min_elevation_deg: float

    model_config = ConfigDict(from_attributes=True)


# ── Pass Event schemas ─────────────────────────────────────────────────────────

class PassEventResponse(BaseModel):
    id: int
    satellite_id: int
    station_id: int
    aos_time: datetime
    los_time: datetime
    duration_seconds: float
    max_elevation_deg: float
    max_elevation_time: Optional[datetime] = None
    aos_azimuth_deg: Optional[float] = None
    los_azimuth_deg: Optional[float] = None
    doppler_shift_hz: Optional[float] = None
    quality_score: float
    is_scheduled: bool

    model_config = ConfigDict(from_attributes=True)


class PassEventWithNames(PassEventResponse):
    satellite_name: Optional[str] = None
    station_name: Optional[str] = None


# ── Operation result schemas ───────────────────────────────────────────────────

class FetchResult(BaseModel):
    fetched: bool
    satellite_count: int
    source: str
    fetched_at: Optional[datetime] = None
    message: str = ""


class PropagationResult(BaseModel):
    satellites_processed: int
    satellites_failed: int
    stations_count: int
    total_passes: int
    elapsed_seconds: float
    passes_per_second: float
    start_time: str


class SchedulerResult(BaseModel):
    window_start: str
    window_end: str
    stations_processed: int
    passes_considered: int
    passes_scheduled: int
    unique_satellites_covered: int
    schedule_efficiency_pct: float


class NetworkStats(BaseModel):
    total_satellites: int
    total_stations: int
    total_passes: int
    scheduled_passes: int
    unique_satellites_covered: int
    busiest_stations: List[dict]
