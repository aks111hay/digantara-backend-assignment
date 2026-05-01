# 50 ground stations spread across all continents and major orbital coverage zones
# Fields: name, country, latitude (°N), longitude (°E), elevation_m, min_elevation_deg

GROUND_STATIONS = [
    # North America
    {"name": "New York",         "country": "USA",           "latitude":  40.7128,  "longitude":  -74.0060, "elevation_m":  10.0, "min_elevation_deg": 5.0},
    {"name": "Los Angeles",      "country": "USA",           "latitude":  34.0522,  "longitude": -118.2437, "elevation_m":  71.0, "min_elevation_deg": 5.0},
    {"name": "Chicago",          "country": "USA",           "latitude":  41.8781,  "longitude":  -87.6298, "elevation_m": 181.0, "min_elevation_deg": 5.0},
    {"name": "Houston",          "country": "USA",           "latitude":  29.7604,  "longitude":  -95.3698, "elevation_m":  15.0, "min_elevation_deg": 5.0},
    {"name": "Fairbanks",        "country": "USA",           "latitude":  64.8378,  "longitude": -147.7164, "elevation_m": 136.0, "min_elevation_deg": 5.0},
    {"name": "Toronto",          "country": "Canada",        "latitude":  43.6532,  "longitude":  -79.3832, "elevation_m":  76.0, "min_elevation_deg": 5.0},
    {"name": "Vancouver",        "country": "Canada",        "latitude":  49.2827,  "longitude": -123.1207, "elevation_m":   0.0, "min_elevation_deg": 5.0},
    {"name": "Mexico City",      "country": "Mexico",        "latitude":  19.4326,  "longitude":  -99.1332, "elevation_m":2240.0, "min_elevation_deg": 5.0},

    # South America
    {"name": "Brasilia",         "country": "Brazil",        "latitude": -15.7975,  "longitude":  -47.8919, "elevation_m":1172.0, "min_elevation_deg": 5.0},
    {"name": "Buenos Aires",     "country": "Argentina",     "latitude": -34.6037,  "longitude":  -58.3816, "elevation_m":  25.0, "min_elevation_deg": 5.0},
    {"name": "Bogota",           "country": "Colombia",      "latitude":   4.7110,  "longitude":  -74.0721, "elevation_m":2625.0, "min_elevation_deg": 5.0},
    {"name": "Lima",             "country": "Peru",          "latitude": -12.0464,  "longitude":  -77.0428, "elevation_m": 154.0, "min_elevation_deg": 5.0},

    # Europe
    {"name": "London",           "country": "UK",            "latitude":  51.5074,  "longitude":   -0.1278, "elevation_m":  11.0, "min_elevation_deg": 5.0},
    {"name": "Paris",            "country": "France",        "latitude":  48.8566,  "longitude":    2.3522, "elevation_m":  35.0, "min_elevation_deg": 5.0},
    {"name": "Berlin",           "country": "Germany",       "latitude":  52.5200,  "longitude":   13.4050, "elevation_m":  34.0, "min_elevation_deg": 5.0},
    {"name": "Madrid",           "country": "Spain",         "latitude":  40.4168,  "longitude":   -3.7038, "elevation_m": 667.0, "min_elevation_deg": 5.0},
    {"name": "Rome",             "country": "Italy",         "latitude":  41.9028,  "longitude":   12.4964, "elevation_m":  21.0, "min_elevation_deg": 5.0},
    {"name": "Stockholm",        "country": "Sweden",        "latitude":  59.3293,  "longitude":   18.0686, "elevation_m":  28.0, "min_elevation_deg": 5.0},
    {"name": "Oslo",             "country": "Norway",        "latitude":  59.9139,  "longitude":   10.7522, "elevation_m":  23.0, "min_elevation_deg": 5.0},
    {"name": "Warsaw",           "country": "Poland",        "latitude":  52.2297,  "longitude":   21.0122, "elevation_m": 113.0, "min_elevation_deg": 5.0},

    # Africa
    {"name": "Cairo",            "country": "Egypt",         "latitude":  30.0444,  "longitude":   31.2357, "elevation_m":  23.0, "min_elevation_deg": 5.0},
    {"name": "Lagos",            "country": "Nigeria",       "latitude":   6.5244,  "longitude":    3.3792, "elevation_m":  41.0, "min_elevation_deg": 5.0},
    {"name": "Nairobi",          "country": "Kenya",         "latitude":  -1.2921,  "longitude":   36.8219, "elevation_m":1795.0, "min_elevation_deg": 5.0},
    {"name": "Johannesburg",     "country": "South Africa",  "latitude": -26.2041,  "longitude":   28.0473, "elevation_m":1753.0, "min_elevation_deg": 5.0},
    {"name": "Accra",            "country": "Ghana",         "latitude":   5.6037,  "longitude":   -0.1870, "elevation_m":  61.0, "min_elevation_deg": 5.0},

    # Middle East
    {"name": "Dubai",            "country": "UAE",           "latitude":  25.2048,  "longitude":   55.2708, "elevation_m":   5.0, "min_elevation_deg": 5.0},
    {"name": "Riyadh",           "country": "Saudi Arabia",  "latitude":  24.7136,  "longitude":   46.6753, "elevation_m": 612.0, "min_elevation_deg": 5.0},
    {"name": "Tel Aviv",         "country": "Israel",        "latitude":  32.0853,  "longitude":   34.7818, "elevation_m":  30.0, "min_elevation_deg": 5.0},

    # Asia
    {"name": "Mumbai",           "country": "India",         "latitude":  19.0760,  "longitude":   72.8777, "elevation_m":  14.0, "min_elevation_deg": 5.0},
    {"name": "Bengaluru",        "country": "India",         "latitude":  12.9716,  "longitude":   77.5946, "elevation_m": 920.0, "min_elevation_deg": 5.0},
    {"name": "Delhi",            "country": "India",         "latitude":  28.6139,  "longitude":   77.2090, "elevation_m": 216.0, "min_elevation_deg": 5.0},
    {"name": "Beijing",          "country": "China",         "latitude":  39.9042,  "longitude":  116.4074, "elevation_m":  44.0, "min_elevation_deg": 5.0},
    {"name": "Shanghai",         "country": "China",         "latitude":  31.2304,  "longitude":  121.4737, "elevation_m":   4.0, "min_elevation_deg": 5.0},
    {"name": "Tokyo",            "country": "Japan",         "latitude":  35.6762,  "longitude":  139.6503, "elevation_m":  40.0, "min_elevation_deg": 5.0},
    {"name": "Seoul",            "country": "South Korea",   "latitude":  37.5665,  "longitude":  126.9780, "elevation_m":  38.0, "min_elevation_deg": 5.0},
    {"name": "Singapore",        "country": "Singapore",     "latitude":   1.3521,  "longitude":  103.8198, "elevation_m":  15.0, "min_elevation_deg": 5.0},
    {"name": "Bangkok",          "country": "Thailand",      "latitude":  13.7563,  "longitude":  100.5018, "elevation_m":   2.0, "min_elevation_deg": 5.0},
    {"name": "Karachi",          "country": "Pakistan",      "latitude":  24.8607,  "longitude":   67.0011, "elevation_m":   8.0, "min_elevation_deg": 5.0},
    {"name": "Dhaka",            "country": "Bangladesh",    "latitude":  23.8103,  "longitude":   90.4125, "elevation_m":   8.0, "min_elevation_deg": 5.0},
    {"name": "Colombo",          "country": "Sri Lanka",     "latitude":   6.9271,  "longitude":   79.8612, "elevation_m":   7.0, "min_elevation_deg": 5.0},

    # Central Asia / Russia
    {"name": "Moscow",           "country": "Russia",        "latitude":  55.7558,  "longitude":   37.6173, "elevation_m": 156.0, "min_elevation_deg": 5.0},
    {"name": "Novosibirsk",      "country": "Russia",        "latitude":  54.9885,  "longitude":   82.9207, "elevation_m": 162.0, "min_elevation_deg": 5.0},
    {"name": "Almaty",           "country": "Kazakhstan",    "latitude":  43.2220,  "longitude":   76.8512, "elevation_m": 817.0, "min_elevation_deg": 5.0},

    # Oceania
    {"name": "Sydney",           "country": "Australia",     "latitude": -33.8688,  "longitude":  151.2093, "elevation_m":  39.0, "min_elevation_deg": 5.0},
    {"name": "Melbourne",        "country": "Australia",     "latitude": -37.8136,  "longitude":  144.9631, "elevation_m":  31.0, "min_elevation_deg": 5.0},
    {"name": "Perth",            "country": "Australia",     "latitude": -31.9505,  "longitude":  115.8605, "elevation_m":  60.0, "min_elevation_deg": 5.0},
    {"name": "Auckland",         "country": "New Zealand",   "latitude": -36.8485,  "longitude":  174.7633, "elevation_m":  26.0, "min_elevation_deg": 5.0},

    # Polar / High latitude (important for LEO coverage)
    {"name": "Longyearbyen",     "country": "Norway",        "latitude":  78.2232,  "longitude":   15.6267, "elevation_m":  28.0, "min_elevation_deg": 5.0},
    {"name": "Tromsø",           "country": "Norway",        "latitude":  69.6492,  "longitude":   18.9553, "elevation_m":  10.0, "min_elevation_deg": 5.0},
    {"name": "Ushuaia",          "country": "Argentina",     "latitude": -54.8019,  "longitude":  -68.3030, "elevation_m":  14.0, "min_elevation_deg": 5.0},
]

assert len(GROUND_STATIONS) == 50, f"Expected 50 stations, got {len(GROUND_STATIONS)}"
