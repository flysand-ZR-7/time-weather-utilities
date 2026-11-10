"""Tests for live time, world clock, timezone conversions, and calendar calculations."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_live_time_iana(client: AsyncClient):
    resp = await client.post("/time", json={"timezone": "America/New_York"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "America/New_York"
    assert "utc_offset" in data
    assert "datetime" in data
    assert isinstance(data["is_dst"], bool)
    assert isinstance(data["unix_timestamp"], int)


@pytest.mark.asyncio
async def test_get_live_time_city(client: AsyncClient):
    resp = await client.post("/time", json={"timezone": "Tokyo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "Asia/Tokyo"
    assert data["utc_offset"] == "+09:00"
    assert data["is_dst"] is False


@pytest.mark.asyncio
async def test_get_live_time_with_format_and_at(client: AsyncClient):
    resp = await client.post(
        "/time",
        json={
            "timezone": "Europe/London",
            "at": "2026-07-15T15:30:00",
            "date_format": "%Y/%m/%d %H:%M",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "Europe/London"
    assert data["datetime"] == "2026/07/15 15:30"
    assert data["is_dst"] is True  # July in London is British Summer Time


@pytest.mark.asyncio
async def test_get_live_time_invalid_timezone(client: AsyncClient):
    resp = await client.post("/time", json={"timezone": "Atlantis/Underwater"})
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_TIMEZONE"


@pytest.mark.asyncio
async def test_world_clock_sorting(client: AsyncClient):
    resp = await client.post(
        "/time/world",
        json={"locations": ["Tokyo", "New York", "London"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    offsets = [loc["utc_offset_seconds"] for loc in data["locations"]]
    assert offsets == sorted(offsets)


@pytest.mark.asyncio
async def test_timezone_conversion(client: AsyncClient):
    resp = await client.post(
        "/timezone/convert",
        json={
            "datetime_str": "2026-01-15T12:00:00",
            "from_zone": "America/New_York",
            "to_zone": "Europe/London",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_timezone"] == "America/New_York"
    assert data["target_timezone"] == "Europe/London"
    # In January: NYC is UTC-5, London is UTC+0 -> London is 5 hours ahead
    assert data["utc_difference_hours"] == 5.0
    assert "2026-01-15T17:00:00" in data["target_datetime"]


@pytest.mark.asyncio
async def test_timezone_conversion_dst_warning(client: AsyncClient):
    # During autumn fallback in New York, 1:30 AM occurs twice
    resp = await client.post(
        "/timezone/convert",
        json={
            "datetime_str": "2026-11-01T01:30:00",
            "from_zone": "America/New_York",
            "to_zone": "UTC",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["warning"] is not None
    assert "autumn" in data["warning"] or "fallback" in data["warning"]


@pytest.mark.asyncio
async def test_timezone_search(client: AsyncClient):
    resp = await client.get("/timezone/search", params={"q": "paris"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any("Paris" in tz for tz in data["results"])


@pytest.mark.asyncio
async def test_date_calc_difference(client: AsyncClient):
    resp = await client.post(
        "/date/calc",
        json={
            "operation": "difference",
            "start_date": "2026-01-01",
            "end_date": "2026-01-15",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_days"] == 14
    assert data["total_hours"] == 336
    assert data["business_days"] == 10  # 14 days contains 2 weekends (4 weekend days)


@pytest.mark.asyncio
async def test_date_calc_add_with_month_end_roll(client: AsyncClient):
    # Jan 31 + 1 month should roll to Feb 28 in 2026 (non-leap year)
    resp = await client.post(
        "/date/calc",
        json={
            "operation": "add",
            "start_date": "2026-01-31",
            "months": 1,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result_date"] == "2026-02-28"
    assert data["is_leap_year"] is False


@pytest.mark.asyncio
async def test_date_calc_add_business_days(client: AsyncClient):
    # Friday 2026-01-09 + 2 business days -> Tuesday 2026-01-13
    resp = await client.post(
        "/date/calc",
        json={
            "operation": "add",
            "start_date": "2026-01-09",
            "business_days": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result_date"] == "2026-01-13"
    assert data["day_of_week"] == "Tuesday"


@pytest.mark.asyncio
async def test_date_calc_weekday_and_week_number(client: AsyncClient):
    resp = await client.post(
        "/date/calc",
        json={
            "operation": "weekday",
            "start_date": "2026-01-01",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["day_name"] == "Thursday"
    assert data["is_weekend"] is False

    resp2 = await client.post(
        "/date/calc",
        json={
            "operation": "week_number",
            "start_date": "2026-01-01",
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["iso_week"] == 1


@pytest.mark.asyncio
async def test_date_calc_days_until(client: AsyncClient):
    resp = await client.post(
        "/date/calc",
        json={
            "operation": "days_until",
            "start_date": "2026-01-01",
            "end_date": "2026-01-11",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["days_remaining"] == 10
    assert data["is_past"] is False
