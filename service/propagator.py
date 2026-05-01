import logging
import math
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional

import numpy as np
from sgp4.api import Satrec, WGS84

logger = logging.getLogger(__name__)

# Propagation window
PROPAGATION_DAYS = 7

# Adaptive sampling parameters
# Coarse scan: period/COARSE_DIVISOR — fast sweep to find candidate windows
COARSE_DIVISOR = 20

# Fine scan step during binary search (seconds)
FINE_STEP_SEC = 1.0

# Minimum pass duration to record (seconds)
MIN_PASS_DURATION_SEC = 5.0


def _build_satrec(tle_line1: str, tle_line2: str) -> Optional[Satrec]:
    """
    Build an sgp4 Satrec object from TLE lines.
    Returns None if TLE is invalid.
    """
    try:
        sat = Satrec.twoline2rv(tle_line1, tle_line2, WGS84)
        return sat
    except Exception as exc:
        logger.debug(f"Failed to build Satrec: {exc}")
        return None


def _propagate_to_ecef(sat: Satrec, dt: datetime) -> Optional[Tuple[float, float, float, float, float, float]]:
    """
    Propagate satellite to given UTC datetime.
    Returns (x, y, z, vx, vy, vz) in km and km/s (TEME frame).
    Returns None on propagation error.
    """
    jd_whole = _datetime_to_jd(dt)
    jd_frac = 0.0

    e, r, v = sat.sgp4(jd_whole, jd_frac)
    if e != 0:
        return None  # propagation error (e.g., satellite decayed)

    return r[0], r[1], r[2], v[0], v[1], v[2]


def _datetime_to_jd(dt: datetime) -> float:
    """
    Convert UTC datetime to Julian Date.
    Using the standard formula for J2000.
    """
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    y = dt.year
    m = dt.month
    d = dt.day
    h = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3.6e9

    if m <= 2:
        y -= 1
        m += 12

    A = int(y / 100)
    B = 2 - A + int(A / 4)

    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + h / 24.0 + B - 1524.5
    return jd


def _elevation_from_teme(
    r_teme: Tuple[float, float, float],
    dt: datetime,
    obs_lat_deg: float,
    obs_lon_deg: float,
    obs_alt_km: float,
) -> float:
    """
    Compute elevation angle from observer to satellite.
    Converts TEME position to ECEF via GMST rotation, then to elevation.
    Returns elevation in degrees.
    """
    # Greenwich Mean Sidereal Time
    gmst = _compute_gmst(dt)

    # TEME → ECEF rotation around Z-axis by GMST
    cos_g, sin_g = math.cos(gmst), math.sin(gmst)
    x_ecef = cos_g * r_teme[0] + sin_g * r_teme[1]
    y_ecef = -sin_g * r_teme[0] + cos_g * r_teme[1]
    z_ecef = r_teme[2]

    # Observer ECEF
    lat = math.radians(obs_lat_deg)
    lon = math.radians(obs_lon_deg)
    R = 6371.0 + obs_alt_km
    obs_x = R * math.cos(lat) * math.cos(lon)
    obs_y = R * math.cos(lat) * math.sin(lon)
    obs_z = R * math.sin(lat)

    # Range vector
    rx = x_ecef - obs_x
    ry = y_ecef - obs_y
    rz = z_ecef - obs_z
    r_mag = math.sqrt(rx**2 + ry**2 + rz**2)

    # Zenith unit vector at observer
    zx = math.cos(lat) * math.cos(lon)
    zy = math.cos(lat) * math.sin(lon)
    zz = math.sin(lat)

    # Elevation = angle between range vector and local horizontal plane
    sin_el = (rx * zx + ry * zy + rz * zz) / r_mag
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_el))))


def _compute_gmst(dt: datetime) -> float:
    """
    Compute Greenwich Mean Sidereal Time in radians.
    Uses IAU 1982 formula sufficient for SGP4 (TEME frame).
    """
    jd = _datetime_to_jd(dt)
    T = (jd - 2451545.0) / 36525.0
    gmst_sec = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * T
        + 0.093104 * T**2
        - 6.2e-6 * T**3
    )
    gmst_rad = math.fmod(gmst_sec * (math.pi / 43200.0), 2 * math.pi)
    if gmst_rad < 0:
        gmst_rad += 2 * math.pi
    return gmst_rad


def _get_azimuth(
    r_teme: Tuple[float, float, float],
    dt: datetime,
    obs_lat_deg: float,
    obs_lon_deg: float,
    obs_alt_km: float,
) -> float:
    """Return azimuth in degrees (0=N, 90=E)."""
    gmst = _compute_gmst(dt)
    cos_g, sin_g = math.cos(gmst), math.sin(gmst)
    x_ecef = cos_g * r_teme[0] + sin_g * r_teme[1]
    y_ecef = -sin_g * r_teme[0] + cos_g * r_teme[1]
    z_ecef = r_teme[2]

    lat = math.radians(obs_lat_deg)
    lon = math.radians(obs_lon_deg)
    R = 6371.0 + obs_alt_km
    obs_x = R * math.cos(lat) * math.cos(lon)
    obs_y = R * math.cos(lat) * math.sin(lon)
    obs_z = R * math.sin(lat)

    rx = x_ecef - obs_x
    ry = y_ecef - obs_y
    rz = z_ecef - obs_z

    # SEZ frame
    s = math.sin(lat) * math.cos(lon) * rx + math.sin(lat) * math.sin(lon) * ry - math.cos(lat) * rz
    e = -math.sin(lon) * rx + math.cos(lon) * ry

    az = math.atan2(e, -s)
    return (math.degrees(az) + 360) % 360


def _binary_search_crossing(
    sat: Satrec,
    t_lo: datetime,
    t_hi: datetime,
    obs_lat_deg: float,
    obs_lon_deg: float,
    obs_alt_km: float,
    min_elevation_deg: float,
    find_rising: bool,
    iterations: int = 20,
) -> datetime:
    """
    Binary search for the exact moment satellite crosses min_elevation_deg.
    find_rising=True → find AOS, find_rising=False → find LOS.
    """
    for _ in range(iterations):
        t_mid = t_lo + (t_hi - t_lo) / 2

        result = _propagate_to_ecef(sat, t_mid)
        if result is None:
            return t_mid

        el = _elevation_from_teme(result[:3], t_mid, obs_lat_deg, obs_lon_deg, obs_alt_km)
        above = el >= min_elevation_deg

        if find_rising:
            if above:
                t_hi = t_mid
            else:
                t_lo = t_mid
        else:
            if above:
                t_lo = t_mid
            else:
                t_hi = t_mid

    return t_lo + (t_hi - t_lo) / 2


def propagate_satellite_passes(
    tle_line1: str,
    tle_line2: str,
    satellite_db_id: int,
    mean_motion_rev_per_day: float,
    stations: List[dict],
    start_time: Optional[datetime] = None,
) -> List[dict]:
    """
    Compute all passes for one satellite over all ground stations for 7 days.

    Strategy:
      1. Compute orbital period from mean motion
      2. Coarse scan at period/20 intervals to find candidate windows
      3. Binary search for exact AOS and LOS times
      4. Record pass geometry + quality score

    Args:
        tle_line1, tle_line2: TLE strings
        satellite_db_id:      DB primary key of satellite
        mean_motion_rev_per_day: from TLE line 2, column 53-63
        stations:             list of dicts with id, latitude, longitude, elevation_m, min_elevation_deg
        start_time:           propagation start (default: now UTC)

    Returns:
        List of pass dicts ready for bulk DB insert
    """
    sat = _build_satrec(tle_line1, tle_line2)
    if sat is None:
        return []

    if start_time is None:
        start_time = datetime.now(timezone.utc)

    end_time = start_time + timedelta(days=PROPAGATION_DAYS)

    # Adaptive coarse step based on orbital period
    if mean_motion_rev_per_day > 0:
        period_sec = 86400.0 / mean_motion_rev_per_day
    else:
        period_sec = 5400.0  # default 90 min LEO

    coarse_step = timedelta(seconds=period_sec / COARSE_DIVISOR)

    all_passes = []

    for station in stations:
        obs_lat = station["latitude"]
        obs_lon = station["longitude"]
        obs_alt = station.get("elevation_m", 0.0) / 1000.0  # m → km
        min_el = station.get("min_elevation_deg", 5.0)
        station_id = station["id"]

        t = start_time
        in_pass = False
        pass_start = None
        max_el = -90.0
        max_el_time = None
        aos_az = None

        while t <= end_time:
            result = _propagate_to_ecef(sat, t)

            if result is None:
                # Satellite has decayed
                break

            r_teme = result[:3]
            el = _elevation_from_teme(r_teme, t, obs_lat, obs_lon, obs_alt)
            above = el >= min_el

            if above and not in_pass:
                # Rising edge detected — binary search backward for exact AOS
                t_search_start = max(start_time, t - coarse_step)
                aos = _binary_search_crossing(
                    sat, t_search_start, t,
                    obs_lat, obs_lon, obs_alt, min_el,
                    find_rising=True,
                )
                in_pass = True
                pass_start = aos
                max_el = el
                max_el_time = t

                # AOS azimuth
                aos_result = _propagate_to_ecef(sat, aos)
                if aos_result:
                    aos_az = _get_azimuth(aos_result[:3], aos, obs_lat, obs_lon, obs_alt)

            elif above and in_pass:
                # Track maximum elevation
                if el > max_el:
                    max_el = el
                    max_el_time = t

            elif not above and in_pass:
                # Falling edge — binary search for exact LOS
                los = _binary_search_crossing(
                    sat, t - coarse_step, t,
                    obs_lat, obs_lon, obs_alt, min_el,
                    find_rising=False,
                )
                in_pass = False

                duration = (los - pass_start).total_seconds()

                if duration >= MIN_PASS_DURATION_SEC:
                    # LOS azimuth
                    los_result = _propagate_to_ecef(sat, los)
                    los_az = None
                    if los_result:
                        los_az = _get_azimuth(los_result[:3], los, obs_lat, obs_lon, obs_alt)

                    # Doppler: compute at max elevation for peak shift
                    max_el_result = _propagate_to_ecef(sat, max_el_time) if max_el_time else None
                    doppler = 0.0
                    if max_el_result:
                        from app.utils.math_helpers import compute_doppler_shift_hz
                        doppler = compute_doppler_shift_hz(
                            max_el_result[3], max_el_result[4], max_el_result[5],
                            max_el_result[0], max_el_result[1], max_el_result[2],
                            obs_lat, obs_lon, obs_alt,
                        )

                    from app.utils.math_helpers import compute_quality_score
                    quality = compute_quality_score(max_el, duration, abs(doppler) / max(duration, 1))

                    all_passes.append({
                        "satellite_id": satellite_db_id,
                        "station_id": station_id,
                        "aos_time": pass_start,
                        "los_time": los,
                        "duration_seconds": round(duration, 2),
                        "max_elevation_deg": round(max_el, 3),
                        "max_elevation_time": max_el_time,
                        "aos_azimuth_deg": round(aos_az, 2) if aos_az is not None else None,
                        "los_azimuth_deg": round(los_az, 2) if los_az is not None else None,
                        "doppler_shift_hz": round(doppler, 2),
                        "quality_score": quality,
                        "is_scheduled": False,
                    })

            t += coarse_step

        # Handle pass still in progress at end of window
        if in_pass and pass_start:
            duration = (end_time - pass_start).total_seconds()
            if duration >= MIN_PASS_DURATION_SEC:
                from app.utils.math_helpers import compute_quality_score
                quality = compute_quality_score(max_el, duration)
                all_passes.append({
                    "satellite_id": satellite_db_id,
                    "station_id": station_id,
                    "aos_time": pass_start,
                    "los_time": end_time,
                    "duration_seconds": round(duration, 2),
                    "max_elevation_deg": round(max_el, 3),
                    "max_elevation_time": max_el_time,
                    "aos_azimuth_deg": round(aos_az, 2) if aos_az is not None else None,
                    "los_azimuth_deg": None,
                    "doppler_shift_hz": None,
                    "quality_score": quality,
                    "is_scheduled": False,
                })

    return all_passes
