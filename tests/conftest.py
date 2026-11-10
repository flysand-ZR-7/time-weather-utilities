"""Pytest test configuration, fixtures, and application test clients."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.cache import (
    air_quality_cache,
    currency_list_cache,
    currency_rates_cache,
    forecast_cache,
    geocoding_cache,
    weather_cache,
)
from app.main import app
from app.ratelimit import rate_limiter
from app.upstream import budget_tracker, close_http_client, init_http_client


@pytest.fixture(autouse=True)
def reset_caches_and_limits():
    """Clear caches, reset rate limiter records, and reset budget counter before each test."""
    geocoding_cache.clear()
    weather_cache.clear()
    forecast_cache.clear()
    air_quality_cache.clear()
    currency_rates_cache.clear()
    currency_list_cache.clear()

    rate_limiter._records.clear()
    budget_tracker.reset_for_test(count=0)
    yield


@pytest.fixture
async def client():
    """Async test client bound to FastAPI application with lifespan management."""
    await init_http_client()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    await close_http_client()
