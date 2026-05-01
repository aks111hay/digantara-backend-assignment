from sqlalchemy import (
    Column, Integer, Float, DateTime,
    ForeignKey, Boolean, Index
)
from sqlalchemy.orm import relationship
from db.base import Base


class PassEvent(Base):
    __tablename__ = "pass_events"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    satellite_id = Column(Integer, ForeignKey("satellites.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("ground_stations.id"), nullable=False)

    # Core pass timing
    aos_time = Column(DateTime(timezone=True), nullable=False)   # Acquisition of Signal
    los_time = Column(DateTime(timezone=True), nullable=False)   # Loss of Signal
    duration_seconds = Column(Float, nullable=False)

    # Pass geometry
    max_elevation_deg = Column(Float, nullable=False)            # peak elevation angle
    max_elevation_time = Column(DateTime(timezone=True), nullable=True)

    # Astrodynamics quality metrics
    aos_azimuth_deg = Column(Float, nullable=True)               # azimuth at AOS
    los_azimuth_deg = Column(Float, nullable=True)               # azimuth at LOS
    doppler_shift_hz = Column(Float, nullable=True)              # max Doppler at 437 MHz

    # Quality score 0.0 - 1.0
    # Weighted combination of elevation, duration, doppler rate
    quality_score = Column(Float, nullable=False, default=0.0)

    # Scheduling flag — set by scheduler after optimization
    is_scheduled = Column(Boolean, nullable=False, default=False)

    # Relationships
    satellite = relationship("Satellite", back_populates="passes")
    station = relationship("GroundStation", back_populates="passes")

    # -----------------------------------------------------------------------
    # Composite indexes for sub-second query performance
    # -----------------------------------------------------------------------
    __table_args__ = (
        # Most common query: passes for a station in a time window
        Index("ix_pass_station_aos", "station_id", "aos_time", "los_time"),

        # Satellite timeline queries
        Index("ix_pass_satellite_aos", "satellite_id", "aos_time"),

        # Scheduler queries: unscheduled passes ordered by quality
        Index("ix_pass_scheduled_quality", "is_scheduled", "quality_score"),

        # Time range scans across all stations
        Index("ix_pass_aos_time", "aos_time"),
    )

    def __repr__(self):
        return (
            f"<PassEvent sat={self.satellite_id} stn={self.station_id} "
            f"aos={self.aos_time} dur={self.duration_seconds:.1f}s "
            f"el={self.max_elevation_deg:.1f}°>"
        )
