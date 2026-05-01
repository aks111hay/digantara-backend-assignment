from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone

from app.models.satellite import Satellite


class SatelliteRepository:

    def __init__(self, db: Session):
        self.db = db

    def upsert_many(self, satellites_data: List[dict]) -> int:
        """
        Insert or update satellites by norad_id.
        Returns count of upserted rows.
        """
        count = 0
        for data in satellites_data:
            existing = self.db.execute(
                select(Satellite).where(Satellite.norad_id == data["norad_id"])
            ).scalar_one_or_none()

            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                self.db.add(Satellite(**data))
            count += 1

        self.db.commit()
        return count

    def get_all(self) -> List[Satellite]:
        return self.db.execute(select(Satellite)).scalars().all()

    def get_by_norad_id(self, norad_id: int) -> Optional[Satellite]:
        return self.db.execute(
            select(Satellite).where(Satellite.norad_id == norad_id)
        ).scalar_one_or_none()

    def get_by_constellation(self, constellation: str) -> List[Satellite]:
        return self.db.execute(
            select(Satellite).where(Satellite.constellation == constellation.upper())
        ).scalars().all()

    def get_stale(self, older_than_hours: float = 2.0) -> List[Satellite]:
        """Return satellites whose TLE data needs refresh."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        return self.db.execute(
            select(Satellite).where(Satellite.fetched_at < cutoff)
        ).scalars().all()

    def count(self) -> int:
        from sqlalchemy import func
        return self.db.execute(
            select(func.count()).select_from(Satellite)
        ).scalar_one()

    def get_last_fetch_time(self) -> Optional[datetime]:
        from sqlalchemy import func
        return self.db.execute(
            select(func.max(Satellite.fetched_at))
        ).scalar_one_or_none()
