"""Tests for currency exchange, multi-target conversion, and time-series trends."""

import pytest
import respx
from httpx import AsyncClient, Response
from app.config import settings

MOCK_CURRENCIES = {
    "USD": "United States Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "JPY": "Japanese Yen",
    "CAD": "Canadian Dollar",
}

MOCK_LATEST_RATES = {
    "amount": 1.0,
    "base": "USD",
    "date": "2026-10-23",
    "rates": {
        "EUR": 0.895,
        "GBP": 0.775,
        "JPY": 152.4,
    },
}

MOCK_TREND_RATES = {
    "amount": 1.0,
    "base": "USD",
    "start_date": "2026-09-24",
    "end_date": "2026-10-23",
    "rates": {
        "2026-09-24": {"EUR": 0.880},
        "2026-10-01": {"EUR": 0.885},
        "2026-10-15": {"EUR": 0.890},
        "2026-10-23": {"EUR": 0.895},
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_currency_convert_latest(client: AsyncClient):
    currencies_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/currencies"
    latest_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/latest"

    respx.get(currencies_url).mock(return_value=Response(200, json=MOCK_CURRENCIES))
    respx.get(latest_url).mock(return_value=Response(200, json=MOCK_LATEST_RATES))

    resp = await client.post(
        "/currency",
        json={"amount": 100, "from_currency": "USD", "to_currencies": ["EUR", "GBP"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 100
    assert data["base_currency"] == "USD"
    assert data["conversions"]["EUR"]["converted_amount"] == 89.5
    assert data["conversions"]["GBP"]["converted_amount"] == 77.5


@pytest.mark.asyncio
@respx.mock
async def test_currency_convert_same_base_and_target(client: AsyncClient):
    currencies_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/currencies"
    respx.get(currencies_url).mock(return_value=Response(200, json=MOCK_CURRENCIES))

    resp = await client.post(
        "/currency",
        json={"amount": 50, "from_currency": "USD", "to_currencies": ["USD"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rates"]["USD"] == 1.0
    assert data["conversions"]["USD"]["converted_amount"] == 50.0


@pytest.mark.asyncio
@respx.mock
async def test_currency_convert_historical_date(client: AsyncClient):
    currencies_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/currencies"
    hist_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/2026-01-15"

    respx.get(currencies_url).mock(return_value=Response(200, json=MOCK_CURRENCIES))
    respx.get(hist_url).mock(
        return_value=Response(
            200,
            json={"amount": 1.0, "base": "USD", "date": "2026-01-15", "rates": {"EUR": 0.850}},
        )
    )

    resp = await client.post(
        "/currency",
        json={"amount": 100, "from_currency": "USD", "to_currencies": ["EUR"], "date": "2026-01-15"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-01-15"
    assert data["conversions"]["EUR"]["converted_amount"] == 85.0


@pytest.mark.asyncio
@respx.mock
async def test_currency_list(client: AsyncClient):
    currencies_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/currencies"
    respx.get(currencies_url).mock(return_value=Response(200, json=MOCK_CURRENCIES))

    resp = await client.get("/currency/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 5
    assert "EUR" in data["currencies"]


@pytest.mark.asyncio
@respx.mock
async def test_currency_trend_analysis(client: AsyncClient):
    currencies_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/currencies"
    respx.get(currencies_url).mock(return_value=Response(200, json=MOCK_CURRENCIES))

    # Catch any date range query to frankfurter
    trend_pattern = rf"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/\d{{4}}-\d{{2}}-\d{{2}}\.\.\d{{4}}-\d{{2}}-\d{{2}}"
    respx.get(url__regex=trend_pattern).mock(return_value=Response(200, json=MOCK_TREND_RATES))

    resp = await client.post(
        "/currency/trend",
        json={"from_currency": "USD", "to_currency": "EUR", "days": 30},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_rate"] == 0.880
    assert data["max_rate"] == 0.895
    assert data["trend_direction"] == "up"  # 0.880 to 0.895 is an upward trend
    assert data["change_percent"] > 0


@pytest.mark.asyncio
@respx.mock
async def test_currency_unsupported_code(client: AsyncClient):
    currencies_url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/currencies"
    respx.get(currencies_url).mock(return_value=Response(200, json=MOCK_CURRENCIES))

    resp = await client.post(
        "/currency",
        json={"amount": 100, "from_currency": "FAKE", "to_currencies": ["EUR"]},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "CURRENCY_ERROR"
