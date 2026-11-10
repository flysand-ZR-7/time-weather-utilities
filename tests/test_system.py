"""Tests for system health check, Open-Meteo daily budget limits, rate limiting, and unified error format."""

import pytest
import respx
from httpx import AsyncClient, Response
from app.config import settings
from app.upstream import budget_tracker


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "time-weather-utilities"
    assert "open_meteo_budget" in data
    assert "cache_stats" in data
    assert "non-commercial free tier" in data["attribution_notice"]


@pytest.mark.asyncio
@respx.mock
async def test_open_meteo_budget_blocking(client: AsyncClient):
    # Simulate counter at 9,500 calls (the daily block threshold)
    budget_tracker.reset_for_test(count=settings.OPEN_METEO_BLOCK_LIMIT)

    resp = await client.post("/weather/current", json={"location": "London"})
    assert resp.status_code == 503
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UPSTREAM_BUDGET_EXCEEDED"
    assert "budget reached" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_validation_error_format(client: AsyncClient):
    # Missing required field 'timezone'
    resp = await client.post("/time", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "validation_errors" in data["error"]["details"]


@pytest.mark.asyncio
async def test_rate_limiting_enforcement(client: AsyncClient):
    # Test rate limiter by triggering more than limit within 60s
    for _ in range(settings.RATE_LIMIT_PER_MINUTE):
        resp = await client.post("/calc", json={"expression": "1 + 1"})
        assert resp.status_code == 200

    # 61st request should be rejected with HTTP 429
    blocked_resp = await client.post("/calc", json={"expression": "1 + 1"})
    assert blocked_resp.status_code == 429
    data = blocked_resp.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in blocked_resp.headers
