"""FastAPI application entrypoint with lifespan, rate limiting, and unified error handling."""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.cache import get_cache_stats
from app.config import settings
from app.models import HealthResponse, StandardErrorResponse
from app.ratelimit import RateLimitMiddleware
from app.routers import calc, currency, time as time_router, units, weather
from app.services.weather import ATTRIBUTION_STATEMENT
from app.upstream import budget_tracker, close_http_client, init_http_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("time_weather_plugin")

start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle resources."""
    global start_time
    start_time = time.time()
    logger.info("Initializing Time, Weather & Utilities Plugin...")
    await init_http_client()
    yield
    logger.info("Shutting down Time, Weather & Utilities Plugin...")
    await close_http_client()


app = FastAPI(
    title="Time, Weather & Utilities Plugin",
    description=(
        "Comprehensive live API plugin providing 7 core capabilities for AI assistants: "
        "Live Time, Time Zones, Weather & Forecasts, Air Quality & Lifestyle Advice, "
        "Safe AST Math Calculator, Unit Converter, and Currency Exchange."
    ),
    version="1.0.0",
    lifespan=lifespan,
    responses={
        400: {"model": StandardErrorResponse, "description": "Bad Request"},
        404: {"model": StandardErrorResponse, "description": "Not Found"},
        422: {"model": StandardErrorResponse, "description": "Unprocessable / Validation Error"},
        429: {"model": StandardErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": StandardErrorResponse, "description": "Internal Server Error"},
        502: {"model": StandardErrorResponse, "description": "Upstream Gateway Error"},
        503: {"model": StandardErrorResponse, "description": "Service / Budget Unavailable"},
    },
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", "An error occurred.")
        details = exc.detail.get("details", {})
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)
        details = {}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        errors.append({
            "field": loc,
            "message": err.get("msg"),
            "type": err.get("type"),
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed. Please check field requirements and types.",
                "details": {"validation_errors": errors},
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": {"error_type": type(exc).__name__},
            }
        },
    )


# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------

app.include_router(time_router.router)
app.include_router(weather.router)
app.include_router(calc.router)
app.include_router(units.router)
app.include_router(currency.router)


# ---------------------------------------------------------------------------
# Health & Status Endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check and resource metrics",
    description="Inspect service status, uptime, Open-Meteo free-tier daily call budget, and cache statistics.",
)
async def health_endpoint() -> HealthResponse:
    uptime = max(0.0, round(time.time() - start_time, 2)) if start_time > 0 else 0.0
    return HealthResponse(
        status="healthy",
        service="time-weather-utilities",
        version="1.0.0",
        uptime_seconds=uptime,
        open_meteo_budget=budget_tracker.get_stats(),
        cache_stats=get_cache_stats(),
        attribution_notice=ATTRIBUTION_STATEMENT,
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
