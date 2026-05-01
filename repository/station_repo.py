from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional

from app.models.ground_station import GroundStation


class StationRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[GroundStation]:
        return self.db.execute(select(GroundStation)).scalars().all()

    def get_by_id(self, station_id: int) -> Optional[GroundStation]:
        return self.db.execute(
            select(GroundStation).where(GroundStation.id == station_id)
        ).scalar_one_or_none()

    def get_by_country(self, country: str) -> List[GroundStation]:
        return self.db.execute(
            select(GroundStation).where(GroundStation.country == country)
        ).scalars().all()

    def count(self) -> int:
        from sqlalchemy import func
        return self.db.execute(
            select(func.count()).select_from(GroundStation)
        ).scalar_one()
