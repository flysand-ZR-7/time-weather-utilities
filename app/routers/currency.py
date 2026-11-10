"""API routes for currency exchange rates, supported currencies, and time-series trends."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.models import (
    CurrencyConvertRequest,
    CurrencyConvertResponse,
    CurrencyListResponse,
    CurrencyTrendRequest,
    CurrencyTrendResponse,
)
from app.services.currency import (
    convert_currency,
    get_currency_trend,
    get_supported_currencies,
)
from app.upstream import UpstreamAPIError

router = APIRouter(prefix="/currency", tags=["Currency Exchange"])


@router.post(
    "",
    response_model=CurrencyConvertResponse,
    summary="Convert currency rates",
    description="Convert an amount from a base currency into up to 10 target currencies using European Central Bank reference rates via the Frankfurter API.",
)
async def currency_convert_endpoint(payload: CurrencyConvertRequest) -> Dict[str, Any]:
    try:
        return await convert_currency(
            amount=payload.amount,
            from_currency=payload.from_currency,
            to_currencies=payload.to_currencies,
            historical_date=payload.date,
        )
    except UpstreamAPIError as u_err:
        raise HTTPException(
            status_code=u_err.status_code,
            detail={"code": "UPSTREAM_ERROR", "message": u_err.message, "details": u_err.details},
        ) from u_err
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "CURRENCY_ERROR", "message": str(val_err)},
        ) from val_err


@router.get(
    "/list",
    response_model=CurrencyListResponse,
    summary="List supported currencies",
    description="Retrieve all supported 3-letter currency codes and their official names.",
)
async def currency_list_endpoint() -> Dict[str, Any]:
    try:
        currencies = await get_supported_currencies()
        return {
            "count": len(currencies),
            "currencies": currencies,
        }
    except UpstreamAPIError as u_err:
        raise HTTPException(
            status_code=u_err.status_code,
            detail={"code": "UPSTREAM_ERROR", "message": u_err.message},
        ) from u_err


@router.post(
    "/trend",
    response_model=CurrencyTrendResponse,
    summary="Historical currency trend",
    description="Compute 7 or 30-day exchange rate trends, minimum, maximum, and average rates between two currencies.",
)
async def currency_trend_endpoint(payload: CurrencyTrendRequest) -> Dict[str, Any]:
    try:
        return await get_currency_trend(
            from_currency=payload.from_currency,
            to_currency=payload.to_currency,
            days=payload.days,
        )
    except UpstreamAPIError as u_err:
        raise HTTPException(
            status_code=u_err.status_code,
            detail={"code": "UPSTREAM_ERROR", "message": u_err.message},
        ) from u_err
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "CURRENCY_TREND_ERROR", "message": str(val_err)},
        ) from val_err
