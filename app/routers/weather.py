"""API routes for current weather, weather forecasts, air quality, and lifestyle advice."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.models import (
    AirQualityRequest,
    AirQualityResponse,
    CurrentWeatherRequest,
    CurrentWeatherResponse,
    ForecastRequest,
    ForecastResponse,
    WeatherAdviceRequest,
    WeatherAdviceResponse,
)
from app.services.geocode import PlaceNotFoundError
from app.services.weather import (
    get_air_quality,
    get_current_weather,
    get_forecast,
    get_weather_advice,
)
from app.upstream import UpstreamAPIError, UpstreamBudgetExceededError

router = APIRouter(prefix="/weather", tags=["Weather & Environment"])


@router.post(
    "/current",
    response_model=CurrentWeatherResponse,
    summary="Get current weather",
    description="Retrieve live weather conditions for a place name or coordinates, with WMO interpretation, compass wind headings, and non-commercial attribution.",
)
async def current_weather_endpoint(payload: CurrentWeatherRequest) -> Dict[str, Any]:
    try:
        return await get_current_weather(
            location_query=payload.location,
            temperature_unit=payload.temperature_unit,
            wind_speed_unit=payload.wind_speed_unit,
            precipitation_unit=payload.precipitation_unit,
        )
    except PlaceNotFoundError as p_err:
        raise HTTPException(
            status_code=404,
            detail={"code": "LOCATION_NOT_FOUND", "message": str(p_err)},
        ) from p_err
    except UpstreamBudgetExceededError as b_err:
        raise HTTPException(
            status_code=503,
            detail={"code": "UPSTREAM_BUDGET_EXCEEDED", "message": str(b_err)},
        ) from b_err
    except UpstreamAPIError as u_err:
        raise HTTPException(
            status_code=u_err.status_code,
            detail={"code": "UPSTREAM_ERROR", "message": u_err.message, "details": u_err.details},
        ) from u_err
    except ValueError as v_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_PARAMETERS", "message": str(v_err)},
        ) from v_err


@router.post(
    "/forecast",
    response_model=ForecastResponse,
    summary="Get weather forecast",
    description="Retrieve 1 to 16-day forecast with daily highs/lows, rain probabilities, optional hourly breakdowns, sun/moon phases, and a plain language narrative summary.",
)
async def forecast_endpoint(payload: ForecastRequest) -> Dict[str, Any]:
    try:
        return await get_forecast(
            location_query=payload.location,
            forecast_days=payload.forecast_days,
            forecast_hours=payload.forecast_hours,
            include_hourly=payload.include_hourly,
            include_astronomy=payload.include_astronomy,
            temperature_unit=payload.temperature_unit,
            wind_speed_unit=payload.wind_speed_unit,
            precipitation_unit=payload.precipitation_unit,
        )
    except PlaceNotFoundError as p_err:
        raise HTTPException(
            status_code=404,
            detail={"code": "LOCATION_NOT_FOUND", "message": str(p_err)},
        ) from p_err
    except UpstreamBudgetExceededError as b_err:
        raise HTTPException(
            status_code=503,
            detail={"code": "UPSTREAM_BUDGET_EXCEEDED", "message": str(b_err)},
        ) from b_err
    except UpstreamAPIError as u_err:
        raise HTTPException(
            status_code=u_err.status_code,
            detail={"code": "UPSTREAM_ERROR", "message": u_err.message, "details": u_err.details},
        ) from u_err
    except ValueError as v_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_PARAMETERS", "message": str(v_err)},
        ) from v_err


@router.post(
    "/air-quality",
    response_model=AirQualityResponse,
    summary="Get air quality and pollutants",
    description="Retrieve European and US AQI indices, PM2.5, PM10, Ozone, UV index, actionable health guidance, and pollen concentrations.",
)
async def air_quality_endpoint(payload: AirQualityRequest) -> Dict[str, Any]:
    try:
        return await get_air_quality(location_query=payload.location)
    except PlaceNotFoundError as p_err:
        raise HTTPException(
            status_code=404,
            detail={"code": "LOCATION_NOT_FOUND", "message": str(p_err)},
        ) from p_err
    except UpstreamBudgetExceededError as b_err:
        raise HTTPException(
            status_code=503,
            detail={"code": "UPSTREAM_BUDGET_EXCEEDED", "message": str(b_err)},
        ) from b_err
    except UpstreamAPIError as u_err:
        raise HTTPException(
            status_code=u_err.status_code,
            detail={"code": "UPSTREAM_ERROR", "message": u_err.message, "details": u_err.details},
        ) from u_err
    except ValueError as v_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_PARAMETERS", "message": str(v_err)},
        ) from v_err


@router.post(
    "/advice",
    response_model=WeatherAdviceResponse,
    summary="Actionable weather and lifestyle advice",
    description="Receive lifestyle advice: umbrella recommendation, jacket clothing type, sunscreen guidance, heat risks, wind gusts, and a 0-10 outdoor comfort score.",
)
async def weather_advice_endpoint(payload: WeatherAdviceRequest) -> Dict[str, Any]:
    try:
        return await get_weather_advice(location_query=payload.location)
    except PlaceNotFoundError as p_err:
        raise HTTPException(
            status_code=404,
            detail={"code": "LOCATION_NOT_FOUND", "message": str(p_err)},
        ) from p_err
    except UpstreamBudgetExceededError as b_err:
        raise HTTPException(
            status_code=503,
            detail={"code": "UPSTREAM_BUDGET_EXCEEDED", "message": str(b_err)},
        ) from b_err
    except UpstreamAPIError as u_err:
        raise HTTPException(
            status_code=u_err.status_code,
            detail={"code": "UPSTREAM_ERROR", "message": u_err.message, "details": u_err.details},
        ) from u_err
    except ValueError as v_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_PARAMETERS", "message": str(v_err)},
        ) from v_err
