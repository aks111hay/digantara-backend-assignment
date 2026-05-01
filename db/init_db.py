from sqlalchemy.orm import Session
from db.base import Base, engine
from models import satellite, ground_station, pass_event  # noqa: F401 — ensures models are registered
from utils.ground_stations import GROUND_STATIONS
from models.ground_station import GroundStation
from logger import get_logger

logger = get_logger()


def init_db() -> None:
    """
    Create all tables and seed ground stations if not already present.
    Safe to call multiple times — will not drop existing data.
    """
    logger.info("Initialising database...")

    # Enable WAL mode for better SQLite concurrent read performance
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("PRAGMA journal_mode=WAL"))
        conn.execute(__import__("sqlalchemy").text("PRAGMA synchronous=NORMAL"))
        conn.execute(__import__("sqlalchemy").text("PRAGMA cache_size=-64000"))  # 64MB cache
        conn.execute(__import__("sqlalchemy").text("PRAGMA temp_store=MEMORY"))
        conn.commit()

    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created.")

    # Seed ground stations
    with Session(engine) as session:
        existing = session.query(GroundStation).count()
        if existing == 0:
            stations = [
                GroundStation(**gs) for gs in GROUND_STATIONS
            ]
            session.add_all(stations)
            session.commit()
            logger.info(f"Seeded {len(stations)} ground stations.")
        else:
            logger.info(f"Ground stations already seeded ({existing} found).")
