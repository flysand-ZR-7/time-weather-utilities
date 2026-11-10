"""In-memory caching system with category-specific TTLCache instances."""

from typing import Any, Dict
from cachetools import TTLCache
from app.config import settings

# Thread-safe in-memory TTL caches
geocoding_cache: TTLCache[str, Any] = TTLCache(maxsize=2000, ttl=settings.CACHE_GEOCODING_TTL)
weather_cache: TTLCache[str, Any] = TTLCache(maxsize=2000, ttl=settings.CACHE_WEATHER_TTL)
forecast_cache: TTLCache[str, Any] = TTLCache(maxsize=2000, ttl=settings.CACHE_FORECAST_TTL)
air_quality_cache: TTLCache[str, Any] = TTLCache(maxsize=2000, ttl=settings.CACHE_AIR_QUALITY_TTL)
currency_rates_cache: TTLCache[str, Any] = TTLCache(maxsize=2000, ttl=settings.CACHE_CURRENCY_RATES_TTL)
currency_list_cache: TTLCache[str, Any] = TTLCache(maxsize=10, ttl=settings.CACHE_CURRENCY_LIST_TTL)


def round_coord(val: float) -> float:
    """Round coordinate to 2 decimal places (~1.1 km precision) to maximize cache hits."""
    return round(val, 2)


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Return operational statistics across all TTL caches."""
    return {
        "geocoding": {
            "current_size": len(geocoding_cache),
            "max_size": geocoding_cache.maxsize,
            "ttl_seconds": geocoding_cache.ttl,
        },
        "weather": {
            "current_size": len(weather_cache),
            "max_size": weather_cache.maxsize,
            "ttl_seconds": weather_cache.ttl,
        },
        "forecast": {
            "current_size": len(forecast_cache),
            "max_size": forecast_cache.maxsize,
            "ttl_seconds": forecast_cache.ttl,
        },
        "air_quality": {
            "current_size": len(air_quality_cache),
            "max_size": air_quality_cache.maxsize,
            "ttl_seconds": air_quality_cache.ttl,
        },
        "currency_rates": {
            "current_size": len(currency_rates_cache),
            "max_size": currency_rates_cache.maxsize,
            "ttl_seconds": currency_rates_cache.ttl,
        },
        "currency_list": {
            "current_size": len(currency_list_cache),
            "max_size": currency_list_cache.maxsize,
            "ttl_seconds": currency_list_cache.ttl,
        },
    }
