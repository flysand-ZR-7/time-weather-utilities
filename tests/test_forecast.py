"""Tests for weather forecast generation, hourly breakdowns, and astronomy."""

import pytest
import respx
from httpx import AsyncClient, Response
from app.config import settings

MOCK_GEO = {
    "results": [
        {
            "id": 1,
            "name": "London",
            "latitude": 51.5,
            "longitude": -0.12,
            "country": "United Kingdom",
            "timezone": "Europe/London",
        }
    ]
}

MOCK_FORECAST = {
    "latitude": 51.5,
    "longitude": -0.12,
    "daily_units": {
        "temperature_2m_max": "°C",
        "precipitation_sum": "mm",
    },
    "daily": {
        "time": ["2026-10-24", "2026-10-25"],
        "weather_code": [0, 61],  # Clear sky, Slight rain
        "temperature_2m_max": [18.2, 14.5],
        "temperature_2m_min": [9.0, 8.2],
        "apparent_temperature_max": [17.5, 13.0],
        "apparent_temperature_min": [8.0, 7.0],
        "precipitation_sum": [0.0, 4.5],
        "precipitation_probability_max": [10, 85],
        "wind_speed_10m_max": [15.0, 22.0],
        "wind_gusts_10m_max": [25.0, 40.0],
        "uv_index_max": [3.2, 1.5],
        "sunrise": ["2026-10-24T07:38", "2026-10-25T07:40"],
        "sunset": ["2026-10-24T17:49", "2026-10-25T17:47"],
        "daylight_duration": [36660, 36420],
        "sunshine_duration": [28000, 10000],
    },
    "hourly_units": {
        "temperature_2m": "°C",
    },
    "hourly": {
        "time": ["2026-10-24T00:00", "2026-10-24T01:00"],
        "temperature_2m": [11.0, 10.5],
        "apparent_temperature": [10.0, 9.5],
        "precipitation_probability": [0, 0],
        "precipitation": [0.0, 0.0],
        "relative_humidity_2m": [75, 78],
        "wind_speed_10m": [8.0, 8.5],
        "weather_code": [0, 0],
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_forecast_daily_and_summary(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO))
    respx.get(settings.OPEN_METEO_FORECAST_URL).mock(return_value=Response(200, json=MOCK_FORECAST))

    resp = await client.post(
        "/weather/forecast",
        json={"location": "London", "forecast_days": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["daily"]) == 2
    assert "Forecast for the next 2 days" in data["summary"]
    assert "Precipitation" in data["summary"]
    assert data["daily"][0]["weather_description"] == "Clear sky"
    assert data["daily"][1]["weather_description"] == "Slight rain"


@pytest.mark.asyncio
@respx.mock
async def test_forecast_astronomy_and_moon_phase(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO))
    respx.get(settings.OPEN_METEO_FORECAST_URL).mock(return_value=Response(200, json=MOCK_FORECAST))

    resp = await client.post(
        "/weather/forecast",
        json={"location": "London", "forecast_days": 2, "include_astronomy": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    day1 = data["daily"][0]
    assert "astronomy" in day1
    assert "moon_phase" in day1["astronomy"]
    assert isinstance(day1["astronomy"]["moon_illumination"], (int, float))
    assert day1["astronomy"]["daylight_duration_seconds"] == 36660


@pytest.mark.asyncio
@respx.mock
async def test_forecast_hourly_inclusion(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO))
    respx.get(settings.OPEN_METEO_FORECAST_URL).mock(return_value=Response(200, json=MOCK_FORECAST))

    resp = await client.post(
        "/weather/forecast",
        json={"location": "London", "forecast_days": 2, "include_hourly": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["hourly"] is not None
    assert len(data["hourly"]) == 2
    assert data["hourly"][0]["temperature"] == 11.0
