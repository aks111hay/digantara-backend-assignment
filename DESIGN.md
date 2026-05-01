# System Design & Implementation Strategy

## 1. Problem Analysis
The task requires predicting satellite passes for ~6000 satellites over 50 ground stations for a 7-day window. This presents several technical challenges:
- **Scale:** ~6000 satellites × 50 stations = 300,000 potential pairings. 
- **Computational Cost:** SGP4 propagation is CPU-intensive. A brute-force 1-second sampling for 7 days (604,800 points) per pairing is infeasible ($3 \times 10^5 \times 6 \times 10^5 = 1.8 \times 10^{11}$ points).
- **Data Volume:** Millions of pass events need to be stored and queried with sub-second latency.
- **Scheduling Optimization:** Resolving conflicts when multiple satellites are visible to the same station simultaneously.

---

## 2. Software Architecture
The system follows a modular microservice-ready architecture built with **FastAPI**.

### Core Components:
1.  **Ingestion Engine (`fetcher.py`):** Automates TLE retrieval from CelesTrak. Implements a 2-hour caching layer to respect source rate limits.
2.  **Propagation Engine (`propagator.py`):** The "brain" of the system. It handles SGP4 calculations and geometric transformations (TEME → ECEF → Topocentric).
3.  **Optimization Engine (`scheduler.py`):** Implements a greedy interval scheduling algorithm to maximize network utilization.
4.  **Storage Layer:** SQLite with **WAL (Write-Ahead Logging)** mode enabled and heavy indexing for high-performance concurrent reads.

---

## 3. Implementation Strategy & Algorithmic Thinking

### A. Adaptive SGP4 Sampling (The "Speed-up")
Instead of fixed-interval sampling, I implemented an **adaptive temporal scan**:
1.  **Period-Based Step:** For each satellite, we derive the orbital period from the TLE Mean Motion. We set the coarse scan step to `period / 20`. This ensures we never skip a potential pass while minimizing SGP4 calls.
2.  **Edge Detection:** We scan the 7-day window. When a transition from "below horizon" to "above horizon" is detected, we trigger a **Binary Search**.
3.  **Binary Search Refinement:** We perform 20 iterations of binary search to find the exact AOS (Acquisition of Signal) and LOS (Loss of Signal) times with **sub-second precision**.
4.  **Efficiency:** This reduces SGP4 calls by **>95%** compared to a 10-second brute-force scan while maintaining higher precision.

### B. Scheduling Optimization
The requirement is to maximize the number of objects trackable. 
- **Constraint:** Each ground station has a single antenna (one satellite at a time).
- **Algorithm:** I used the **Greedy Earliest Deadline First (EDF)** approach.
- **Why EDF?** In interval scheduling, selecting the interval that ends first is provably optimal for maximizing the number of non-overlapping tasks on a single resource.
- **Quality Weighting:** In cases of ties, I use a custom `quality_score` (based on max elevation and duration) to ensure we pick the "best" pass for the mission.

### C. Database & Query Performance
To achieve sub-second query times with millions of rows:
- **Composite Indexing:** Created specific indexes like `(station_id, aos_time, los_time)` and `(is_scheduled, quality_score)`.
- **Bulk Operations:** Used SQLAlchemy's `insert().values()` for bulk inserts, which is significantly faster than standard ORM object mapping.
- **WAL Mode:** Enabled WAL to allow the API to read data even while the background propagator is writing millions of new rows.

---

## 4. Scalability & Production Readiness

While the prototype uses SQLite, the design is "Postgres-ready":
1.  **Parallelism:** Propagation is implemented as a **Celery/Redis** task. In production, this can be scaled across hundreds of workers, partitioning satellites by NORAD ID ranges.
2.  **Time-Series Optimization:** For production, switching to **TimescaleDB** would allow automatic partitioning by `aos_time`, making deletions of old passes near-instant.
3.  **API Rate Limiting:** Implemented a decorator-based rate limiter to protect the propagation and fetching endpoints.

---

## 5. Assumed Parameters
- **Min Elevation:** 5° (industry standard for reliable RF link).
- **Sampling:** Adaptive (as described above).
- **Station Hardware:** Single antenna per station (assumed for the scheduling constraint).
- **Frequency:** Doppler shifts computed at 437 MHz (standard UHF downlink).
