"""Sliding-window rate limiter middleware for IP-based throttling."""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from app.config import settings


class InMemoryRateLimiter:
    """Sliding window rate limiter tracked per client IP."""

    def __init__(self, requests_per_minute: int = 60, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._records: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup_old_records(self, now: float) -> None:
        """Purge entries older than the sliding window."""
        if now - self._last_cleanup < 60:
            return
        cutoff = now - self.window_seconds
        for ip in list(self._records.keys()):
            self._records[ip] = [ts for ts in self._records[ip] if ts > cutoff]
            if not self._records[ip]:
                del self._records[ip]
        self._last_cleanup = now

    def is_allowed(self, client_ip: str) -> tuple[bool, int]:
        """Check whether client_ip is allowed to make a request.
        
        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        with self._lock:
            self._cleanup_old_records(now)
            timestamps = self._records[client_ip]
            cutoff = now - self.window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            self._records[client_ip] = valid_timestamps

            if len(valid_timestamps) >= self.requests_per_minute:
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest_in_window)))
                return False, retry_after

            self._records[client_ip].append(now)
            return True, 0


rate_limiter = InMemoryRateLimiter(
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware enforcing sliding window rate limits."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exempt health and docs endpoints from rate limiting
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Extract client IP, checking X-Forwarded-For if behind a proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        allowed, retry_after = rate_limiter.is_allowed(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute.",
                        "details": {
                            "retry_after_seconds": retry_after,
                            "limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
                        },
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
