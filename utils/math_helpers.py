import math
from datetime import datetime, timezone
from typing import Tuple


# Earth constants
EARTH_RADIUS_KM = 6371.0
MU = 398600.4418          # Earth gravitational parameter km³/s²
J2 = 1.08262668e-3        # J2 perturbation coefficient
SPEED_OF_LIGHT = 299792.458  # km/s


def degrees_to_radians(deg: float) -> float:
    return math.radians(deg)


def radians_to_degrees(rad: float) -> float:
    return math.degrees(rad)


def ecef_to_geodetic(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Convert ECEF (km) to geodetic lat/lon/alt.
    Uses iterative Bowring method.
    Returns: (latitude_deg, longitude_deg, altitude_km)
    """
    a = 6378.137          # Earth semi-major axis km
    f = 1 / 298.257223563
    b = a * (1 - f)
    e2 = 1 - (b / a) ** 2

    lon = math.atan2(y, x)
    p = math.sqrt(x ** 2 + y ** 2)
    lat = math.atan2(z, p * (1 - e2))

    for _ in range(5):
        sin_lat = math.sin(lat)
        N = a / math.sqrt(1 - e2 * sin_lat ** 2)
        lat = math.atan2(z + e2 * N * sin_lat, p)

    sin_lat = math.sin(lat)
    N = a / math.sqrt(1 - e2 * sin_lat ** 2)
    alt = p / math.cos(lat) - N if abs(math.cos(lat)) > 1e-10 else abs(z) / abs(sin_lat) - N * (1 - e2)

    return math.degrees(lat), math.degrees(lon), alt


def compute_elevation_azimuth(
    sat_x: float, sat_y: float, sat_z: float,
    obs_lat_deg: float, obs_lon_deg: float, obs_alt_km: float
) -> Tuple[float, float]:
    """
    Compute elevation and azimuth angles from an observer to a satellite.
    All positions in km (ECI or ECEF — must be consistent).
    Returns: (elevation_deg, azimuth_deg)
    """
    lat = math.radians(obs_lat_deg)
    lon = math.radians(obs_lon_deg)

    # Observer ECEF position
    cos_lat, sin_lat = math.cos(lat), math.sin(lat)
    cos_lon, sin_lon = math.cos(lon), math.sin(lon)

    obs_x = (EARTH_RADIUS_KM + obs_alt_km) * cos_lat * cos_lon
    obs_y = (EARTH_RADIUS_KM + obs_alt_km) * cos_lat * sin_lon
    obs_z = (EARTH_RADIUS_KM + obs_alt_km) * sin_lat

    # Range vector (satellite - observer)
    rx = sat_x - obs_x
    ry = sat_y - obs_y
    rz = sat_z - obs_z
    r = math.sqrt(rx**2 + ry**2 + rz**2)

    # Transform to South-East-Zenith (SEZ) frame
    s = sin_lat * cos_lon * rx + sin_lat * sin_lon * ry - cos_lat * rz
    e = -sin_lon * rx + cos_lon * ry
    z_comp = cos_lat * cos_lon * rx + cos_lat * sin_lon * ry + sin_lat * rz

    # Elevation
    elevation = math.asin(z_comp / r)

    # Azimuth (measured from North, clockwise)
    azimuth = math.atan2(e, -s)

    return math.degrees(elevation), (math.degrees(azimuth) + 360) % 360


def compute_doppler_shift_hz(
    sat_vx: float, sat_vy: float, sat_vz: float,
    sat_x: float, sat_y: float, sat_z: float,
    obs_lat_deg: float, obs_lon_deg: float, obs_alt_km: float,
    carrier_freq_hz: float = 437e6
) -> float:
    """
    Compute Doppler shift at a given carrier frequency.
    Satellite velocity in km/s, positions in km.
    Default carrier: 437 MHz (common amateur/small sat frequency).
    Returns: Doppler shift in Hz (positive = approaching)
    """
    lat = math.radians(obs_lat_deg)
    lon = math.radians(obs_lon_deg)
    cos_lat, sin_lat = math.cos(lat), math.sin(lat)
    cos_lon, sin_lon = math.cos(lon), math.sin(lon)

    obs_x = (EARTH_RADIUS_KM + obs_alt_km) * cos_lat * cos_lon
    obs_y = (EARTH_RADIUS_KM + obs_alt_km) * cos_lat * sin_lon
    obs_z = (EARTH_RADIUS_KM + obs_alt_km) * sin_lat

    rx = sat_x - obs_x
    ry = sat_y - obs_y
    rz = sat_z - obs_z
    r = math.sqrt(rx**2 + ry**2 + rz**2)

    # Radial velocity (range rate) in km/s
    range_rate = (sat_vx * rx + sat_vy * ry + sat_vz * rz) / r

    # Doppler formula: Δf = -f₀ * v_r / c
    doppler = -carrier_freq_hz * (range_rate / SPEED_OF_LIGHT)
    return doppler


def compute_quality_score(
    max_elevation_deg: float,
    duration_seconds: float,
    doppler_rate_hz_per_s: float = 0.0,
) -> float:
    """
    Compute a 0.0–1.0 quality score for a pass.

    Weights:
      - Max elevation (50%): Higher is better (better link budget)
      - Duration (35%):      Longer pass = more data transfer time
      - Doppler rate (15%):  Lower rate = easier to track

    Elevation scoring: 5° = 0.0, 90° = 1.0
    Duration scoring:  5s = 0.0, 600s (10 min) = 1.0 (capped)
    Doppler rate:      0 Hz/s = 1.0, 5000 Hz/s = 0.0 (capped)
    """
    # Elevation score
    el_score = max(0.0, min(1.0, (max_elevation_deg - 5.0) / 85.0))

    # Duration score
    dur_score = max(0.0, min(1.0, (duration_seconds - 5.0) / 595.0))

    # Doppler rate score (lower is better for tracking difficulty)
    dop_score = max(0.0, 1.0 - abs(doppler_rate_hz_per_s) / 5000.0)

    return round(0.50 * el_score + 0.35 * dur_score + 0.15 * dop_score, 4)


def orbital_period_seconds(mean_motion_rev_per_day: float) -> float:
    """
    Convert TLE mean motion (rev/day) to orbital period in seconds.
    """
    if mean_motion_rev_per_day <= 0:
        return 5400.0  # default ~90 min LEO
    return 86400.0 / mean_motion_rev_per_day


def tle_epoch_to_datetime(tle_line1: str) -> datetime:
    """
    Parse TLE Line 1 epoch field (columns 19-32) into a UTC datetime.
    Format: YYDDD.DDDDDDDD (2-digit year + day of year + fractional day)
    """
    epoch_str = tle_line1[18:32].strip()
    year_2digit = int(epoch_str[:2])
    year = 2000 + year_2digit if year_2digit < 57 else 1900 + year_2digit
    day_of_year = float(epoch_str[2:])

    day_int = int(day_of_year)
    frac_day = day_of_year - day_int

    from datetime import timedelta
    epoch_dt = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_int - 1)
    epoch_dt += timedelta(seconds=frac_day * 86400)
    return epoch_dt


def classify_confidence(epoch_dt: datetime) -> str:
    """
    Rate TLE age confidence based on how old the epoch is.
    SGP4 positional error grows ~1-3 km/day.
    """
    now = datetime.now(timezone.utc)
    age_days = (now - epoch_dt).total_seconds() / 86400.0

    if age_days < 1.0:
        return "fresh"
    elif age_days < 3.0:
        return "good"
    else:
        return "stale"


def extract_constellation(name: str) -> str:
    """
    Derive constellation name from satellite name prefix.
    """
    name_upper = name.upper().strip()
    known = [
        "STARLINK", "ONEWEB", "IRIDIUM", "GLOBALSTAR", "GPS",
        "GLONASS", "GALILEO", "BEIDOU", "ORBCOMM", "SPIRE",
        "PLANET", "ICEYE", "LEMUR", "FLOCK"
    ]
    for k in known:
        if name_upper.startswith(k):
            return k
    return "OTHER"
