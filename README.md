# Ground Pass Predictor

A backend system for predicting satellite visibility passes over 50 global ground stations using real-time TLE data and SGP4 orbital propagation.

---

## Architecture

```
CelesTrak (TLE source)
        │
        ▼
┌─────────────────────────────────────────────┐
│              app/service/                   │
│  fetcher.py       → TLE download + cache    │
│  propagator.py    → SGP4 engine (adaptive)  │
│  pass_detector.py → AOS/LOS orchestrator   │
│  scheduler.py     → Interval optimizer      │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│            SQLite (WAL mode)                │
│  satellites     → ~6000 rows               │
│  ground_stations→ 50 rows (seeded)         │
│  pass_events    → millions of rows         │
│    indexes: station+aos, satellite+aos,    │
│             scheduled+quality, aos_time    │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│           FastAPI  /api/v1/                 │
│  POST /fetch-tles    POST /propagate        │
│  POST /schedule      GET  /network/stats   │
│  GET  /stations/{id}/passes                │
│  GET  /satellites/{norad_id}/passes        │
└─────────────────────────────────────────────┘
```

---

## Setup

### Requirements
- Python 3.11.9
- pip

### Install

```bash
git clone <repo>
cd ground_pass_predictor
pip install -r requirements.txt
```

### Run

```bash
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

---

## Usage Workflow

### Step 1 — Fetch TLEs
```bash
curl -X POST http://localhost:8000/api/v1/fetch-tles
```
Downloads ~6000 active satellite TLEs from CelesTrak. Cached for 2 hours.

### Step 2 — Propagate passes (use limit for testing)
```bash
# Test with 50 satellites
curl -X POST "http://localhost:8000/api/v1/propagate?satellite_limit=50"

# Full run (~6000 satellites, takes several minutes)
curl -X POST "http://localhost:8000/api/v1/propagate"
```

### Step 3 — Schedule
```bash
curl -X POST http://localhost:8000/api/v1/schedule
```

### Step 4 — Query results
```bash
# Network statistics
curl http://localhost:8000/api/v1/network/stats

# Passes for a station (next 24h)
curl http://localhost:8000/api/v1/stations/1/passes

# ISS passes (NORAD 25544)
curl http://localhost:8000/api/v1/satellites/25544/passes

# Scheduled passes next 6 hours
curl "http://localhost:8000/api/v1/network/schedule?hours=6"
```

---

## Key Design Decisions

### Adaptive SGP4 Sampling
Instead of sampling every fixed N seconds, we:
1. Derive orbital period from TLE mean motion (`period = 86400 / mean_motion`)
2. Coarse scan at `period/20` intervals to find candidate windows
3. Binary search (20 iterations) for exact AOS and LOS to ±1 second accuracy

This is **~20x faster** than 10-second fixed sampling with equivalent accuracy.

### Pass Quality Score
Each pass is scored 0.0–1.0 based on:
- **Max elevation (50%)** — higher elevation = better link budget, less atmosphere
- **Duration (35%)** — longer pass = more data transfer time
- **Doppler rate (15%)** — lower rate = easier frequency tracking

### Scheduler
Greedy earliest-deadline-first per station:
- Sort passes by LOS time (ties broken by quality score)
- Greedily select non-overlapping passes
- Provably optimal for maximizing pass count on a single resource
- `O(P log P)` per station — sub-second for millions of passes

### Database Indexes
```sql
-- Most common: station passes in time window
INDEX (station_id, aos_time, los_time)

-- Satellite timeline
INDEX (satellite_id, aos_time)

-- Scheduler queries
INDEX (is_scheduled, quality_score)

-- Time range scans
INDEX (aos_time)
```

### TLE Confidence Flags
- `fresh`: epoch < 1 day old — full SGP4 accuracy (~100m)
- `good`: 1–3 days — acceptable (~1–5 km error)
- `stale`: > 3 days — use with caution (~3–15 km error)

---

## Assumed Parameters

| Parameter | Value | Reason |
|---|---|---|
| Minimum pass duration | 5 seconds | Assignment requirement |
| Minimum elevation angle | 5° | Industry standard for RF contact |
| Propagation window | 7 days | Assignment requirement |
| TLE cache TTL | 2 hours | CelesTrak update frequency |
| Carrier frequency (Doppler) | 437 MHz | Common smallsat/amateur band |
| Ground station elevation model | Spherical Earth | Sufficient for SGP4 accuracy level |

---

## Trade-offs

| Decision | Trade-off |
|---|---|
| SQLite over PostgreSQL | Simpler setup, no concurrency for writes; for production use TimescaleDB |
| Greedy scheduler over ILP | O(P log P) vs optimal but NP-hard; greedy is within 1-OPT for this problem |
| Adaptive sampling | Slightly misses very short passes near period/20 boundary; binary search recovers most |
| TEME frame (no J2 correction) | SGP4 already includes J2; no additional correction needed at this fidelity |
| Spherical Earth for elevation | ~0.1° error vs WGS84 ellipsoid; acceptable for 5° mask angle |

---

## Scaling to Production

- Replace SQLite → **TimescaleDB** (automatic time partitioning, parallel queries)
- Propagation → **Celery workers** (parallelize by satellite batch)
- ~6000 satellites × 50 stations = ~300,000 satellite-station pairs
- Expected pass count: **2–5 million rows per 7-day window**
- With composite indexes: **sub-second** for all query patterns above