from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class Satellite(Base):
    __tablename__ = "satellites"

    id = Column(Integer, primary_key=True, index=True)
    norad_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, index=True)
    tle_line1 = Column(Text, nullable=False)
    tle_line2 = Column(Text, nullable=False)

    # TLE epoch — when this TLE was valid
    epoch = Column(DateTime(timezone=True), nullable=True)

    # TLE age confidence flag
    # "fresh" < 1 day, "good" 1-3 days, "stale" > 3 days
    confidence = Column(String(10), nullable=False, default="fresh")

    # Constellation derived from name prefix e.g. STARLINK, ONEWEB
    constellation = Column(String(50), nullable=True, index=True)

    fetched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to passes
    passes = relationship("PassEvent", back_populates="satellite", lazy="dynamic")

    def __repr__(self):
        return f"<Satellite {self.norad_id} {self.name}>"
