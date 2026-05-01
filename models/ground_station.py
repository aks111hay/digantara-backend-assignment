from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from app.db.base import Base


class GroundStation(Base):
    __tablename__ = "ground_stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)   # degrees, -90 to +90
    longitude = Column(Float, nullable=False)  # degrees, -180 to +180
    elevation_m = Column(Float, nullable=False, default=0.0)  # metres ASL

    # Minimum elevation angle for a valid pass (degrees above horizon)
    min_elevation_deg = Column(Float, nullable=False, default=5.0)

    # Relationship to passes
    passes = relationship("PassEvent", back_populates="station", lazy="dynamic")

    def __repr__(self):
        return f"<GroundStation {self.id} {self.name} ({self.latitude:.2f}, {self.longitude:.2f})>"
