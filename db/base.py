from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pathlib import Path

# Ensure data directory exists
DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_DIR}/passes.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,    # needed for SQLite + FastAPI
        "timeout": 30,
    },
    echo=False,                        # set True to debug SQL
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency — yields a DB session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
