"""Tests for air quality index, pollutant concentrations, and health advice."""

import pytest
import respx
from httpx import AsyncClient, Response
from app.config import settings

MOCK_GEO = {
    "results": [
        {"id": 1, "name": "Berlin", "latitude": 52.52, "longitude": 13.405, "country": "Germany"}
    ]
}

MOCK_AQ_GOOD = {
    "latitude": 52.52,
    "longitude": 13.4,
    "current_units": {"pm2_5": "μg/m³", "pm10": "μg/m³"},
    "current": {
        "time": "2026-10-24T12:00",
        "us_aqi": 28,
        "european_aqi": 18,
        "pm2_5": 6.8,
        "pm10": 11.2,
        "carbon_monoxide": 150.0,
        "nitrogen_dioxide": 12.0,
        "sulphur_dioxide": 1.2,
        "ozone": 45.0,
        "dust": 0.0,
        "uv_index": 2.1,
        "grass_pollen": 5.0,
        "birch_pollen": 0.0,
    },
}

MOCK_AQ_UNHEALTHY = {
    "latitude": 52.52,
    "longitude": 13.4,
    "current_units": {"pm2_5": "μg/m³"},
    "current": {
        "time": "2026-10-24T12:00",
        "us_aqi": 165,
        "european_aqi": 75,
        "pm2_5": 82.5,
        "pm10": 110.0,
        "carbon_monoxide": 800.0,
        "nitrogen_dioxide": 45.0,
        "sulphur_dioxide": 15.0,
        "ozone": 95.0,
        "dust": 20.0,
        "uv_index": 6.0,
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_air_quality_good(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO))
    respx.get(settings.OPEN_METEO_AIR_QUALITY_URL).mock(return_value=Response(200, json=MOCK_AQ_GOOD))

    resp = await client.post("/weather/air-quality", json={"location": "Berlin"})
    assert resp.status_code == 200
    data = resp.json()
    curr = data["current"]
    assert curr["aqi_us"] == 28
    assert curr["category"] == "Good"
    assert "satisfactory" in curr["health_tip"]
    assert curr["pollen"] is not None
    assert curr["pollen"]["grass_pollen"] == 5.0


@pytest.mark.asyncio
@respx.mock
async def test_air_quality_unhealthy(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO))
    respx.get(settings.OPEN_METEO_AIR_QUALITY_URL).mock(return_value=Response(200, json=MOCK_AQ_UNHEALTHY))

    resp = await client.post("/weather/air-quality", json={"location": "Berlin"})
    assert resp.status_code == 200
    data = resp.json()
    curr = data["current"]
    assert curr["aqi_us"] == 165
    assert curr["category"] == "Unhealthy"
    assert "prolonged outdoor exertion" in curr["health_tip"]
