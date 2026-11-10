"""Application configuration loaded from environment variables and .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for Time, Weather & Utilities service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    # Upstream APIs
    OPEN_METEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
    OPEN_METEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    FRANKFURTER_BASE_URL: str = "https://api.frankfurter.dev/v1"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Open-Meteo Free Tier Daily Budget Limits
    OPEN_METEO_WARN_LIMIT: int = 8000
    OPEN_METEO_BLOCK_LIMIT: int = 9500

    # Cache TTLs (in seconds)
    CACHE_GEOCODING_TTL: int = 86400       # 24 hours
    CACHE_WEATHER_TTL: int = 600           # 10 minutes
    CACHE_FORECAST_TTL: int = 1800         # 30 minutes
    CACHE_AIR_QUALITY_TTL: int = 1800      # 30 minutes
    CACHE_CURRENCY_RATES_TTL: int = 3600   # 1 hour
    CACHE_CURRENCY_LIST_TTL: int = 86400   # 24 hours


settings = Settings()
