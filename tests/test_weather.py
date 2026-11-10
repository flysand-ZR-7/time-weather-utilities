"""Tests for current weather observations and lifestyle advice."""

import pytest
import respx
from httpx import AsyncClient, Response
from app.config import settings

MOCK_GEO_RESPONSE = {
    "results": [
        {
            "id": 2643743,
            "name": "London",
            "latitude": 51.50853,
            "longitude": -0.12574,
            "country": "United Kingdom",
            "admin1": "England",
            "timezone": "Europe/London",
        }
    ]
}

MOCK_CURRENT_WEATHER_RESPONSE = {
    "latitude": 51.5,
    "longitude": -0.12,
    "current_units": {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "precipitation": "mm",
        "wind_speed_10m": "km/h",
        "pressure_msl": "hPa",
    },
    "current": {
        "time": "2026-10-24T12:00",
        "temperature_2m": 16.5,
        "apparent_temperature": 15.0,
        "relative_humidity_2m": 65,
        "is_day": 1,
        "precipitation": 0.0,
        "weather_code": 1,  # "Mainly clear"
        "cloud_cover": 25,
        "pressure_msl": 1015.2,
        "surface_pressure": 1014.0,
        "wind_speed_10m": 14.5,
        "wind_direction_10m": 220,  # SW
        "wind_gusts_10m": 28.0,
    },
}

MOCK_AIR_QUALITY_RESPONSE = {
    "latitude": 51.5,
    "longitude": -0.12,
    "current_units": {"pm2_5": "μg/m³", "uv_index": ""},
    "current": {
        "time": "2026-10-24T12:00",
        "pm2_5": 8.0,
        "pm10": 12.0,
        "uv_index": 4.5,
        "european_aqi": 25,
        "us_aqi": 35,
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_current_weather_by_city(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO_RESPONSE))
    respx.get(settings.OPEN_METEO_FORECAST_URL).mock(return_value=Response(200, json=MOCK_CURRENT_WEATHER_RESPONSE))

    resp = await client.post("/weather/current", json={"location": "London"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["name"] == "London"
    assert data["current"]["temperature"] == 16.5
    assert data["current"]["weather_description"] == "Mainly clear"
    assert data["current"]["wind_direction_compass"] == "SW"
    assert "Open-Meteo.com" in data["source"]
    assert "non-commercial free tier" in data["attribution"]


@pytest.mark.asyncio
@respx.mock
async def test_current_weather_by_coordinates(client: AsyncClient):
    # Geocoding should be bypassed when direct coordinates are provided
    geo_route = respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO_RESPONSE))
    respx.get(settings.OPEN_METEO_FORECAST_URL).mock(return_value=Response(200, json=MOCK_CURRENT_WEATHER_RESPONSE))

    resp = await client.post("/weather/current", json={"location": "51.5074, -0.1278"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["current"]["temperature"] == 16.5
    assert not geo_route.called  # Verifies direct coordinate optimization


@pytest.mark.asyncio
@respx.mock
async def test_current_weather_place_not_found(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json={"results": []}))

    resp = await client.post("/weather/current", json={"location": "NonExistentCityXYZ123"})
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "LOCATION_NOT_FOUND"


@pytest.mark.asyncio
@respx.mock
async def test_weather_advice(client: AsyncClient):
    respx.get(settings.OPEN_METEO_GEOCODING_URL).mock(return_value=Response(200, json=MOCK_GEO_RESPONSE))
    respx.get(settings.OPEN_METEO_FORECAST_URL).mock(return_value=Response(200, json=MOCK_CURRENT_WEATHER_RESPONSE))
    respx.get(settings.OPEN_METEO_AIR_QUALITY_URL).mock(return_value=Response(200, json=MOCK_AIR_QUALITY_RESPONSE))

    resp = await client.post("/weather/advice", json={"location": "London"})
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["comfort_score"] <= 10
    assert "summary" in data
    assert data["advice"]["umbrella"]["needed"] is False
    assert data["advice"]["jacket"]["type"] in ("light", "warm")
    assert data["advice"]["sunscreen"]["needed"] is True  # UV index 4.5 >= 3.0
