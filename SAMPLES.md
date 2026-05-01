# Sample API Outputs

This document provides examples of the system's responses for key endpoints, demonstrating the data structure and information provided.

## 1. Network Statistics
**Endpoint:** `GET /api/v1/network/stats`

```json
{
  "total_satellites": 6421,
  "total_stations": 50,
  "total_passes": 4210582,
  "scheduled_passes": 84210,
  "unique_satellites_covered": 5892,
  "busiest_stations": [
    { "station_id": 48, "pass_count": 95201 },
    { "station_id": 49, "pass_count": 94110 },
    { "station_id": 5, "pass_count": 88204 }
  ]
}
```

---

## 2. Satellite Pass Prediction (ISS - NORAD 25544)
**Endpoint:** `GET /api/v1/satellites/25544/passes`

```json
[
  {
    "id": 4501,
    "satellite_id": 1,
    "station_id": 12,
    "aos_time": "2024-05-01T14:20:15Z",
    "los_time": "2024-05-01T14:31:45Z",
    "duration_seconds": 690.0,
    "max_elevation_deg": 68.4,
    "max_elevation_time": "2024-05-01T14:26:00Z",
    "aos_azimuth_deg": 210.5,
    "los_azimuth_deg": 35.2,
    "doppler_shift_hz": 12450.0,
    "quality_score": 0.89,
    "is_scheduled": true
  },
  {
    "id": 4822,
    "satellite_id": 1,
    "station_id": 15,
    "aos_time": "2024-05-01T15:55:10Z",
    "los_time": "2024-05-01T16:04:30Z",
    "duration_seconds": 560.0,
    "max_elevation_deg": 12.5,
    "max_elevation_time": "2024-05-01T15:59:50Z",
    "aos_azimuth_deg": 180.2,
    "los_azimuth_deg": 290.4,
    "doppler_shift_hz": 8200.0,
    "quality_score": 0.35,
    "is_scheduled": false
  }
]
```

---

## 3. Station Schedule
**Endpoint:** `GET /api/v1/stations/1/passes?scheduled_only=true`

```json
[
  {
    "id": 102,
    "satellite_id": 45,
    "station_id": 1,
    "aos_time": "2024-05-01T10:00:00Z",
    "los_time": "2024-05-01T10:12:00Z",
    "duration_seconds": 720.0,
    "max_elevation_deg": 45.0,
    "is_scheduled": true
  },
  {
    "id": 156,
    "satellite_id": 120,
    "station_id": 1,
    "aos_time": "2024-05-01T10:15:00Z",
    "los_time": "2024-05-01T10:25:00Z",
    "duration_seconds": 600.0,
    "max_elevation_deg": 32.0,
    "is_scheduled": true
  }
]
```

---

## 4. Scheduling Result
**Endpoint:** `POST /api/v1/schedule`

```json
{
  "window_start": "2024-05-01T00:00:00Z",
  "window_end": "2024-05-08T00:00:00Z",
  "stations_processed": 50,
  "passes_considered": 4210582,
  "passes_scheduled": 84210,
  "unique_satellites_covered": 5892,
  "schedule_efficiency_pct": 2.0
}
```
*Note: Low efficiency percentage is expected as we select ~1 pass per 15 mins per station from thousands of overlapping candidates.*
