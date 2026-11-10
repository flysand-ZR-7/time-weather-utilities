"""Open-Meteo Geocoding service with coordinate parsing and 24-hour caching."""

import re
from typing import Any, Dict, Optional
from app.cache import geocoding_cache, round_coord
from app.config import settings
from app.upstream import request_upstream


class PlaceNotFoundError(Exception):
    """Raised when geocoding service cannot locate the specified place name."""
    pass


COORD_PATTERN = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$")


async def resolve_location(query: str) -> Dict[str, Any]:
    """Resolve a location query string (either 'lat,lon' or place name) into coordinates and metadata.
    
    Returns:
        Dict with keys: name, latitude, longitude, country, admin1, timezone, elevation.
    """
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Location query cannot be empty.")

    # 1. Check if user provided direct coordinates 'lat, lon'
    coord_match = COORD_PATTERN.match(clean_query)
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))

        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude {lat} out of valid range [-90, 90].")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude {lon} out of valid range [-180, 180].")

        return {
            "name": f"{lat:.4f}, {lon:.4f}",
            "latitude": lat,
            "longitude": lon,
            "country": None,
            "admin1": None,
            "timezone": "auto",
            "elevation": None,
        }

    # 2. Check 24-hour cache
    cache_key = clean_query.lower()
    if cache_key in geocoding_cache:
        return geocoding_cache[cache_key]

    # 3. Query Open-Meteo Geocoding API
    params = {
        "name": clean_query,
        "count": 5,
        "language": "en",
        "format": "json",
    }

    response = await request_upstream(
        method="GET",
        url=settings.OPEN_METEO_GEOCODING_URL,
        is_open_meteo=True,
        params=params,
    )

    data = response.json()
    results = data.get("results")
    if not results or len(results) == 0:
        raise PlaceNotFoundError(f"Location '{clean_query}' not found. Please verify spelling or specify country.")

    top_result = results[0]
    loc_info = {
        "name": top_result.get("name", clean_query),
        "latitude": float(top_result["latitude"]),
        "longitude": float(top_result["longitude"]),
        "country": top_result.get("country"),
        "admin1": top_result.get("admin1"),
        "timezone": top_result.get("timezone", "auto"),
        "elevation": top_result.get("elevation"),
    }

    # Store in 24h cache
    geocoding_cache[cache_key] = loc_info
    return loc_info
