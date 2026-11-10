"""Tests for physical unit conversions and supported categories catalog."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_convert_temperature_offset(client: AsyncClient):
    # Freezing point
    resp = await client.post(
        "/convert",
        json={"value": 0, "from_unit": "celsius", "to_unit": "fahrenheit"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert round(data["to_value"], 2) == 32.0
    assert "T(°F)" in data["explanation"]

    # Boiling point
    resp2 = await client.post(
        "/convert",
        json={"value": 100, "from_unit": "c", "to_unit": "f"},
    )
    assert resp2.status_code == 200
    assert round(resp2.json()["to_value"], 2) == 212.0


@pytest.mark.asyncio
async def test_convert_digital_storage_mb_vs_mib(client: AsyncClient):
    # 1 Megabyte (10^6 bytes) to Mebibyte (2^20 bytes = 1,048,576 bytes)
    resp = await client.post(
        "/convert",
        json={"value": 1, "from_unit": "MB", "to_unit": "MiB"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert 0.9536 <= data["to_value"] <= 0.9538

    # 1 GiB to MiB (1024 MiB)
    resp2 = await client.post(
        "/convert",
        json={"value": 1, "from_unit": "GiB", "to_unit": "MiB"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["to_value"] == 1024.0


@pytest.mark.asyncio
async def test_convert_length_and_speed(client: AsyncClient):
    # 10 miles to kilometers (10 * 1.60934 = ~16.0934 km)
    resp = await client.post(
        "/convert",
        json={"value": 10, "from_unit": "miles", "to_unit": "km"},
    )
    assert resp.status_code == 200
    assert round(resp.json()["to_value"], 2) == 16.09

    # 60 mph to km/h (~96.56 km/h)
    resp2 = await client.post(
        "/convert",
        json={"value": 60, "from_unit": "mph", "to_unit": "km/h"},
    )
    assert resp2.status_code == 200
    assert round(resp2.json()["to_value"], 1) == 96.6


@pytest.mark.asyncio
async def test_convert_incompatible_dimensions(client: AsyncClient):
    # Cannot convert kilograms (mass) to meters (length)
    resp = await client.post(
        "/convert",
        json={"value": 5, "from_unit": "kg", "to_unit": "meters"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "UNIT_CONVERSION_ERROR"
    assert "incompatible dimensions" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_convert_unknown_unit(client: AsyncClient):
    resp = await client.post(
        "/convert",
        json={"value": 10, "from_unit": "quantum_flux", "to_unit": "meters"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "UNIT_CONVERSION_ERROR"


@pytest.mark.asyncio
async def test_get_supported_unit_categories(client: AsyncClient):
    resp = await client.get("/convert/units")
    assert resp.status_code == 200
    data = resp.json()
    cats = data["categories"]
    assert "temperature" in cats
    assert "digital_storage" in cats
    assert "length" in cats
    assert "mass" in cats
    assert "speed" in cats
