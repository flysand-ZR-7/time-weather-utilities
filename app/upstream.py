"""Upstream HTTP client management, retry logic, and Open-Meteo daily budget tracking."""

import asyncio
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional
import httpx
from app.config import settings

logger = logging.getLogger("time_weather_plugin.upstream")

_http_client: Optional[httpx.AsyncClient] = None


class UpstreamBudgetExceededError(Exception):
    """Raised when Open-Meteo daily free-tier call budget is reached."""
    pass


class UpstreamAPIError(Exception):
    """Raised when upstream returns an error or invalid payload."""
    def __init__(self, message: str, status_code: int = 502, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class OpenMeteoBudgetTracker:
    """Thread-safe counter tracking daily calls made to Open-Meteo APIs (resets at UTC midnight)."""

    def __init__(self, warn_limit: int = 8000, block_limit: int = 9500):
        self.warn_limit = warn_limit
        self.block_limit = block_limit
        self._count = 0
        self._current_date = datetime.now(timezone.utc).date()
        self._lock = Lock()

    def _check_and_rollover(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._current_date:
            logger.info("New UTC day detected (%s -> %s). Resetting Open-Meteo call counter.", self._current_date, today)
            self._current_date = today
            self._count = 0

    def record_call(self) -> None:
        """Verify budget and increment the daily call counter."""
        with self._lock:
            self._check_and_rollover()

            if self._count >= self.block_limit:
                logger.error("Open-Meteo daily call budget exceeded (%d/%d). Rejecting request.", self._count, self.block_limit)
                raise UpstreamBudgetExceededError("Daily upstream weather API budget reached. Please try again tomorrow.")

            self._count += 1

            if self._count == self.warn_limit:
                logger.warning("Open-Meteo daily call counter reached warning threshold: %d/%d", self._count, self.block_limit)
            elif self._count > self.warn_limit and self._count % 250 == 0:
                logger.warning("Approaching Open-Meteo daily limit: %d/%d calls used today", self._count, self.block_limit)

    def get_stats(self) -> Dict[str, Any]:
        """Return current daily budget statistics."""
        with self._lock:
            self._check_and_rollover()
            return {
                "utc_date": str(self._current_date),
                "calls_used": self._count,
                "warn_limit": self.warn_limit,
                "block_limit": self.block_limit,
                "remaining_calls": max(0, self.block_limit - self._count),
            }

    def reset_for_test(self, count: int = 0) -> None:
        """Helper for test suites."""
        with self._lock:
            self._count = count
            self._current_date = datetime.now(timezone.utc).date()


budget_tracker = OpenMeteoBudgetTracker(
    warn_limit=settings.OPEN_METEO_WARN_LIMIT,
    block_limit=settings.OPEN_METEO_BLOCK_LIMIT,
)


async def init_http_client() -> None:
    """Initialize shared httpx.AsyncClient during application lifespan startup."""
    global _http_client
    if _http_client is None:
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        _http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
        logger.info("Shared httpx AsyncClient initialized.")


async def close_http_client() -> None:
    """Close shared httpx.AsyncClient during application lifespan shutdown."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("Shared httpx AsyncClient closed.")


def get_http_client() -> httpx.AsyncClient:
    """Return active shared httpx.AsyncClient or fallback instance."""
    if _http_client is not None:
        return _http_client
    # Fallback if accessed outside lifespan (e.g., during isolated testing)
    return httpx.AsyncClient(timeout=10.0)


async def request_upstream(
    method: str,
    url: str,
    is_open_meteo: bool = False,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    """Execute an HTTP request against upstream with automatic single retry and error sanitation."""
    client = get_http_client()

    if is_open_meteo:
        budget_tracker.record_call()

    # First attempt
    try:
        response = await client.request(method, url, params=params, headers=headers)
    except (httpx.TransportError, httpx.TimeoutException) as exc:
        logger.warning("Upstream call failed on first attempt (%s). Retrying in 0.5s...", exc)
        await asyncio.sleep(0.5)
        try:
            response = await client.request(method, url, params=params, headers=headers)
        except Exception as retry_exc:
            logger.error("Upstream call failed on retry: %s", retry_exc)
            raise UpstreamAPIError(
                message=f"Failed to communicate with upstream service: {type(retry_exc).__name__}",
                status_code=504 if isinstance(retry_exc, httpx.TimeoutException) else 502,
            )

    # Handle Open-Meteo specific error payload (HTTP 400 with {"error": true, "reason": "..."})
    if is_open_meteo and response.status_code == 400:
        try:
            err_json = response.json()
            if err_json.get("error"):
                logger.warning("Open-Meteo returned 400 error: %s", err_json.get("reason"))
                raise UpstreamAPIError(
                    message="Weather service rejected parameters. Please verify location or coordinate ranges.",
                    status_code=400,
                    details={"sanitized_reason": "Invalid query parameters provided to weather provider."},
                )
        except (ValueError, KeyError):
            pass

    if response.status_code >= 500:
        logger.error("Upstream service returned %d from %s", response.status_code, url)
        raise UpstreamAPIError(
            message=f"Upstream provider returned server error ({response.status_code}). Please try again later.",
            status_code=502,
        )

    return response
