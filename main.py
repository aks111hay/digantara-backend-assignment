import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.init_db import init_db
from app.api.v1.endpoints import router as v1_router

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: initialise DB, create tables, seed ground stations.
    Shutdown: nothing special needed for SQLite.
    """
    logger.info("=== Ground Pass Predictor starting up ===")
    init_db()
    logger.info("=== Startup complete. API ready. ===")
    yield
    logger.info("=== Shutting down ===")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Ground Pass Predictor",
    description="""
## Space Domain Awareness — Pass Scheduling API

Predict satellite visibility passes over 50 global ground stations
using real-time TLE data and SGP4 orbital propagation.

### Workflow
1. `POST /api/v1/fetch-tles` — Download latest TLEs from CelesTrak
2. `POST /api/v1/propagate` — Run SGP4 for all satellites × 50 stations × 7 days
3. `POST /api/v1/schedule` — Optimise pass scheduling across the network
4. `GET  /api/v1/network/stats` — View network performance metrics

### Key Features
- Adaptive SGP4 sampling (period-based coarse scan + binary search for AOS/LOS)
- Pass quality scoring (elevation, duration, Doppler)
- Greedy weighted interval scheduling per station
- Composite-indexed SQLite for sub-second queries
- TLE age confidence flagging
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(v1_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Ground Pass Predictor",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "ok",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}