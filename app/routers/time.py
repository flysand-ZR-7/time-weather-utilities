"""API routes for live time, world clock, timezone conversion, timezone search, and date calculation."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Query
from app.models import (
    DateCalcRequest,
    TimeRequest,
    TimeResponse,
    TimezoneConvertRequest,
    TimezoneConvertResponse,
    TimezoneSearchResponse,
    WorldClockRequest,
    WorldClockResponse,
)
from app.services.timeutil import (
    calculate_date_operation,
    convert_timezone_times,
    get_live_time,
    search_timezones,
)

router = APIRouter(tags=["Time & Date"])


@router.post(
    "/time",
    response_model=TimeResponse,
    summary="Get live time and timezone details",
    description="Retrieve live wall-clock time, UTC offset, DST status, and calendar day metadata for a city or IANA timezone.",
)
async def get_time_endpoint(payload: TimeRequest) -> Dict[str, Any]:
    try:
        return get_live_time(
            timezone_name=payload.timezone,
            at=payload.at,
            date_format=payload.date_format,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_TIMEZONE", "message": str(exc)},
        ) from exc


@router.post(
    "/time/world",
    response_model=WorldClockResponse,
    summary="Multi-city world clock",
    description="Retrieve current local times for 1 to 10 cities or timezones, returned sorted by UTC offset ascending.",
)
async def get_world_clock_endpoint(payload: WorldClockRequest) -> Dict[str, Any]:
    results = []
    errors = []

    for loc in payload.locations:
        try:
            info = get_live_time(timezone_name=loc, date_format=payload.date_format)
            results.append(info)
        except ValueError as exc:
            errors.append({"location": loc, "error": str(exc)})

    if errors and not results:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_LOCATIONS", "message": "None of the specified locations could be resolved.", "details": errors},
        )

    # Sort results by UTC offset in seconds ascending
    results.sort(key=lambda x: x["utc_offset_seconds"])

    return {
        "count": len(results),
        "locations": results,
    }


@router.post(
    "/timezone/convert",
    response_model=TimezoneConvertResponse,
    summary="Convert datetime between timezones",
    description="Convert a datetime from one timezone or city to another, with automatic detection of DST spring-forward gaps and autumn fallback fold ambiguities.",
)
async def convert_timezone_endpoint(payload: TimezoneConvertRequest) -> Dict[str, Any]:
    try:
        return convert_timezone_times(
            datetime_str=payload.datetime_str,
            from_zone_input=payload.from_zone,
            to_zone_input=payload.to_zone,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "CONVERSION_ERROR", "message": str(exc)},
        ) from exc


@router.get(
    "/timezone/search",
    response_model=TimezoneSearchResponse,
    summary="Search IANA timezones",
    description="Search standard IANA timezones by city name or geographic region.",
)
async def search_timezone_endpoint(
    q: str = Query(..., min_length=1, description="City or region name to search (e.g. 'Tokyo', 'London', 'Chicago')"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of matches to return"),
) -> Dict[str, Any]:
    matches = search_timezones(query=q, limit=limit)
    return {
        "query": q,
        "count": len(matches),
        "results": matches,
    }


@router.post(
    "/date/calc",
    summary="Date mathematics and metadata",
    description="Calculate date difference, add/subtract calendar and business days (with month-end roll handling), find day of week, week number, or days until a target date.",
)
async def date_calc_endpoint(payload: DateCalcRequest) -> Dict[str, Any]:
    try:
        return calculate_date_operation(
            operation=payload.operation,
            start_date=payload.start_date,
            end_date=payload.end_date,
            days=payload.days,
            weeks=payload.weeks,
            months=payload.months,
            years=payload.years,
            business_days=payload.business_days,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "DATE_CALC_ERROR", "message": str(exc)},
        ) from exc
