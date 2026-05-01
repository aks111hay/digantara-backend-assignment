import os
class fetch_const():
    CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    CACHE_TTL_HOURS = 2.0          # re-fetch if data older than 2 hours
    REQUEST_TIMEOUT_SEC = 30
    MAX_SATELLITES = None          # None = fetch all; set int to limit for testing


class pass_detector():
    # Batch size for DB bulk inserts
    INSERT_BATCH_SIZE = 5000
    # Batch size for satellite processing (log progress every N satellites)
    LOG_EVERY_N = 100

class propagator():
    # Propagation window
    PROPAGATION_DAYS = 7
    # Adaptive sampling parameters
    # Coarse scan: period/COARSE_DIVISOR — fast sweep to find candidate windows
    COARSE_DIVISOR = 20
    # Fine scan step during binary search (seconds)
    FINE_STEP_SEC = 1.0
    # Minimum pass duration to record (seconds)
    MIN_PASS_DURATION_SEC = 5.0

class constants():
    # Earth constants
    EARTH_RADIUS_KM = 6371.0
    MU = 398600.4418          # Earth gravitational parameter km³/s²
    J2 = 1.08262668e-3        # J2 perturbation coefficient
    SPEED_OF_LIGHT = 299792.458  # km/s

class Redisconfig:
    # Connection settings
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
