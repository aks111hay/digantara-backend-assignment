from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, update
from typing import List, Optional
from datetime import datetime

from app.models.pass_event import PassEvent


class PassRepository:

    def __init__(self, db: Session):
        self.db = db

    def bulk_insert(self, passes: List[dict]) -> int:
        """
        Bulk insert pass events. Much faster than ORM add() in a loop.
        Returns count inserted.
        """
        if not passes:
            return 0
        self.db.execute(PassEvent.__table__.insert(), passes)
        self.db.commit()
        return len(passes)

    def get_by_station(
        self,
        station_id: int,
        start: datetime,
        end: datetime,
        min_duration_s: float = 5.0,
        min_elevation_deg: float = 0.0,
    ) -> List[PassEvent]:
        """
        Get all passes for a station within a time window.
        Uses ix_pass_station_aos composite index.
        """
        return self.db.execute(
            select(PassEvent).where(
                and_(
                    PassEvent.station_id == station_id,
                    PassEvent.aos_time >= start,
                    PassEvent.los_time <= end,
                    PassEvent.duration_seconds >= min_duration_s,
                    PassEvent.max_elevation_deg >= min_elevation_deg,
                )
            ).order_by(PassEvent.aos_time)
        ).scalars().all()

    def get_by_satellite(
        self,
        satellite_id: int,
        start: datetime,
        end: datetime,
    ) -> List[PassEvent]:
        """
        Get all passes for a satellite within a time window.
        Uses ix_pass_satellite_aos composite index.
        """
        return self.db.execute(
            select(PassEvent).where(
                and_(
                    PassEvent.satellite_id == satellite_id,
                    PassEvent.aos_time >= start,
                    PassEvent.aos_time <= end,
                )
            ).order_by(PassEvent.aos_time)
        ).scalars().all()

    def get_scheduled(
        self,
        start: datetime,
        end: datetime,
    ) -> List[PassEvent]:
        """Return only scheduler-selected passes in a time window."""
        return self.db.execute(
            select(PassEvent).where(
                and_(
                    PassEvent.is_scheduled == True,  # noqa: E712
                    PassEvent.aos_time >= start,
                    PassEvent.los_time <= end,
                )
            ).order_by(PassEvent.station_id, PassEvent.aos_time)
        ).scalars().all()

    def mark_scheduled(self, pass_ids: List[int]) -> None:
        """Bulk-mark passes as scheduled."""
        if not pass_ids:
            return
        self.db.execute(
            update(PassEvent)
            .where(PassEvent.id.in_(pass_ids))
            .values(is_scheduled=True)
        )
        self.db.commit()

    def reset_schedule(self) -> None:
        """Clear all scheduling flags — use before re-running scheduler."""
        self.db.execute(update(PassEvent).values(is_scheduled=False))
        self.db.commit()

    # -----------------------------------------------------------------------
    # Analytics queries
    # -----------------------------------------------------------------------

    def count_total(self) -> int:
        return self.db.execute(
            select(func.count()).select_from(PassEvent)
        ).scalar_one()

    def count_scheduled(self) -> int:
        return self.db.execute(
            select(func.count()).select_from(PassEvent)
            .where(PassEvent.is_scheduled == True)  # noqa: E712
        ).scalar_one()

    def busiest_stations(self, limit: int = 10) -> List[dict]:
        rows = self.db.execute(
            select(
                PassEvent.station_id,
                func.count(PassEvent.id).label("pass_count"),
            )
            .group_by(PassEvent.station_id)
            .order_by(func.count(PassEvent.id).desc())
            .limit(limit)
        ).all()
        return [{"station_id": r.station_id, "pass_count": r.pass_count} for r in rows]

    def unique_satellites_tracked(self) -> int:
        return self.db.execute(
            select(func.count(func.distinct(PassEvent.satellite_id)))
            .where(PassEvent.is_scheduled == True)  # noqa: E712
        ).scalar_one()

    def get_passes_for_station_satellite(
        self, station_id: int, satellite_id: int
    ) -> List[PassEvent]:
        return self.db.execute(
            select(PassEvent).where(
                and_(
                    PassEvent.station_id == station_id,
                    PassEvent.satellite_id == satellite_id,
                )
            ).order_by(PassEvent.aos_time)
        ).scalars().all()

    def delete_all(self) -> None:
        """Wipe pass table — used before re-running full propagation."""
        self.db.execute(PassEvent.__table__.delete())
        self.db.commit()
