from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional

from models.ground_station import GroundStation
from utils.redis_client import redis_client

STATIONS_CACHE_KEY = "all_ground_stations"

class StationRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[GroundStation]:
        """Fetch all stations, checking Redis cache first."""
        # Try cache
        cached = redis_client.get_cache(STATIONS_CACHE_KEY)
        if cached:
            # Convert dicts back to model instances (note: these won't be attached to DB session)
            return [GroundStation(**gs) for gs in cached]

        # Cache miss - fetch from DB
        stations = self.db.execute(select(GroundStation)).scalars().all()
        
        # Store in cache (serialize to dicts first)
        station_dicts = [
            {
                "id": s.id,
                "name": s.name,
                "country": s.country,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "elevation_m": s.elevation_m,
                "min_elevation_deg": s.min_elevation_deg,
            }
            for s in stations
        ]
        redis_client.set_cache(STATIONS_CACHE_KEY, station_dicts, ttl=3600)
        
        return stations

    def get_by_id(self, station_id: int) -> Optional[GroundStation]:
        """Fetch station by ID, checking specific cache key first."""
        cache_key = f"station:{station_id}"
        cached = redis_client.get_cache(cache_key)
        if cached:
            return GroundStation(**cached)

        station = self.db.execute(
            select(GroundStation).where(GroundStation.id == station_id)
        ).scalar_one_or_none()

        if station:
            station_dict = {
                "id": station.id,
                "name": station.name,
                "country": station.country,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "elevation_m": station.elevation_m,
                "min_elevation_deg": station.min_elevation_deg,
            }
            redis_client.set_cache(cache_key, station_dict, ttl=3600)

        return station

    def get_by_country(self, country: str) -> List[GroundStation]:
        return self.db.execute(
            select(GroundStation).where(GroundStation.country == country)
        ).scalars().all()

    def count(self) -> int:
        from sqlalchemy import func
        return self.db.execute(
            select(func.count()).select_from(GroundStation)
        ).scalar_one()
