"""Tests for safe AST calculator and commercial finance operations."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_calc_arithmetic_order_of_operations(client: AsyncClient):
    resp = await client.post("/calc", json={"expression": "2 + 3 * 4 - (10 / 2)"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == 9
    assert data["formatted"] == "9"


@pytest.mark.asyncio
async def test_calc_power_and_caret_syntax(client: AsyncClient):
    resp = await client.post("/calc", json={"expression": "2^10 + 3^2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == 1033


@pytest.mark.asyncio
async def test_calc_constants_and_functions(client: AsyncClient):
    resp = await client.post("/calc", json={"expression": "sqrt(144) * sin(pi / 2) + factorial(5)"})
    assert resp.status_code == 200
    data = resp.json()
    # sqrt(144)=12, sin(pi/2)=1, factorial(5)=120 -> 12 * 1 + 120 = 132
    assert data["result"] == 132


@pytest.mark.asyncio
async def test_calc_division_by_zero(client: AsyncClient):
    resp = await client.post("/calc", json={"expression": "42 / 0"})
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "ZERO_DIVISION"


@pytest.mark.asyncio
async def test_calc_disallow_arbitrary_code(client: AsyncClient):
    # Attempting to execute python builtins or call modules
    resp = await client.post("/calc", json={"expression": "__import__('os').system('dir')"})
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "CALCULATION_ERROR"


@pytest.mark.asyncio
async def test_calc_exponent_guard(client: AsyncClient):
    resp = await client.post("/calc", json={"expression": "2^1500"})
    assert resp.status_code == 422
    data = resp.json()
    assert "safe maximum magnitude" in data["error"]["message"] or "CALCULATION_ERROR" in data["error"]["code"]


@pytest.mark.asyncio
async def test_calc_factorial_guard(client: AsyncClient):
    resp = await client.post("/calc", json={"expression": "factorial(180)"})
    assert resp.status_code == 422
    data = resp.json()
    assert "exceeds safe limit" in data["error"]["message"]


@pytest.mark.asyncio
async def test_finance_percentage(client: AsyncClient):
    # What is 15% of 200?
    resp = await client.post(
        "/calc/finance",
        json={"operation": "percentage", "percent": 15, "value": 200},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == 30.0

    # Percentage change from 50 to 75 (+50%)
    resp2 = await client.post(
        "/calc/finance",
        json={"operation": "percentage", "old_value": 50, "new_value": 75},
    )
    assert resp2.status_code == 200
    assert resp2.json()["result"] == 50.0
    assert resp2.json()["direction"] == "increase"


@pytest.mark.asyncio
async def test_finance_discount(client: AsyncClient):
    # $100 with 20% discount and 8% tax
    resp = await client.post(
        "/calc/finance",
        json={"operation": "discount", "original_price": 100, "discount_percent": 20, "tax_percent": 8},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["discounted_price"] == 80.0
    assert data["tax_amount"] == 6.4
    assert data["final_price"] == 86.4
    assert data["savings"] == 20.0


@pytest.mark.asyncio
async def test_finance_tax(client: AsyncClient):
    # Tax excluded: $100 + 10% = $110
    resp = await client.post(
        "/calc/finance",
        json={"operation": "tax", "amount": 100, "tax_percent": 10, "tax_included": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["net_amount"] == 100.0
    assert data["tax_amount"] == 10.0
    assert data["gross_amount"] == 110.0

    # Tax included: $110 total with 10% tax -> net is $100
    resp2 = await client.post(
        "/calc/finance",
        json={"operation": "tax", "amount": 110, "tax_percent": 10, "tax_included": True},
    )
    assert resp2.status_code == 200
    assert resp2.json()["net_amount"] == 100.0
    assert resp2.json()["tax_amount"] == 10.0


@pytest.mark.asyncio
async def test_finance_tip_split(client: AsyncClient):
    # $100 bill, 20% tip, 4 people
    resp = await client.post(
        "/calc/finance",
        json={"operation": "tip_split", "bill_amount": 100, "tip_percent": 20, "num_people": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tip_amount"] == 20.0
    assert data["total_amount"] == 120.0
    assert data["per_person_total"] == 30.0
    assert data["per_person_tip"] == 5.0


@pytest.mark.asyncio
async def test_finance_simple_interest(client: AsyncClient):
    # $1000 at 5% for 3 years -> $150 interest
    resp = await client.post(
        "/calc/finance",
        json={"operation": "simple_interest", "principal": 1000, "rate_annual_percent": 5, "time_years": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["interest"] == 150.0
    assert data["total_amount"] == 1150.0


@pytest.mark.asyncio
async def test_finance_compound_interest(client: AsyncClient):
    # $1000 at 5% compounded monthly for 1 year
    resp = await client.post(
        "/calc/finance",
        json={
            "operation": "compound_interest",
            "principal": 1000,
            "rate_annual_percent": 5,
            "time_years": 1,
            "compounding_frequency": 12,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert 51.10 <= data["interest"] <= 51.20
    assert 1051.10 <= data["total_amount"] <= 1051.20


@pytest.mark.asyncio
async def test_finance_emi(client: AsyncClient):
    # $100,000 at 8.5% annual interest for 120 months (10 years)
    resp = await client.post(
        "/calc/finance",
        json={"operation": "emi", "principal": 100000, "rate_annual_percent": 8.5, "tenure_months": 120},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert 1239.0 <= data["monthly_emi"] <= 1241.0
    assert data["total_payment"] > 100000
    assert data["total_interest"] > 0
