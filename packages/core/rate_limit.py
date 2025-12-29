"""Rate limiting middleware for Airport API."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable
from functools import wraps

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from packages.core.config import settings
from packages.core.exceptions import RateLimitError

logger = structlog.get_logger()


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Requests per window
    requests: int = 100
    # Window size in seconds
    window: int = 60
    # Key function to identify clients
    key_func: Callable[[Request], str] | None = None


@dataclass
class RateLimitEntry:
    """Track request counts for a client."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production, replace with Redis-based implementation.
    """

    def __init__(self) -> None:
        # client_key -> RateLimitEntry
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        # endpoint -> config
        self._configs: dict[str, RateLimitConfig] = {}
        # Default config
        self._default_config = RateLimitConfig()

    def configure(self, endpoint: str, config: RateLimitConfig) -> None:
        """Configure rate limit for a specific endpoint."""
        self._configs[endpoint] = config

    def configure_default(self, config: RateLimitConfig) -> None:
        """Set default rate limit configuration."""
        self._default_config = config

    def _get_config(self, endpoint: str) -> RateLimitConfig:
        """Get config for endpoint, falling back to default."""
        return self._configs.get(endpoint, self._default_config)

    def _get_client_key(self, request: Request, config: RateLimitConfig) -> str:
        """Get unique key for the client."""
        if config.key_func:
            return config.key_func(request)

        # Default: use IP address + endpoint
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"{client_ip}:{request.url.path}"

    def check(self, request: Request) -> tuple[bool, int, int]:
        """
        Check if request is allowed.

        Returns:
            tuple: (allowed, remaining, retry_after)
        """
        endpoint = request.url.path
        config = self._get_config(endpoint)
        client_key = self._get_client_key(request, config)

        now = time.time()
        entry = self._entries[client_key]

        # Reset window if expired
        if now - entry.window_start >= config.window:
            entry.count = 0
            entry.window_start = now

        # Check if over limit
        if entry.count >= config.requests:
            retry_after = int(config.window - (now - entry.window_start))
            return False, 0, max(1, retry_after)

        # Increment counter
        entry.count += 1
        remaining = config.requests - entry.count

        return True, remaining, 0

    def reset(self, client_key: str) -> None:
        """Reset rate limit for a client."""
        if client_key in self._entries:
            del self._entries[client_key]


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        _configure_default_limits(_rate_limiter)
    return _rate_limiter


def _configure_default_limits(limiter: RateLimiter) -> None:
    """Configure default rate limits for sensitive endpoints."""
    # Strict limits for auth endpoints (from config)
    auth_config = RateLimitConfig(
        requests=settings.rate_limit_auth_requests,
        window=settings.rate_limit_auth_window_seconds,
    )
    limiter.configure("/api/v1/auth/login", auth_config)
    limiter.configure("/api/v1/auth/register", auth_config)
    limiter.configure("/api/v1/auth/forgot-password", RateLimitConfig(requests=3, window=300))
    limiter.configure("/api/v1/auth/reset-password", RateLimitConfig(requests=5, window=300))

    # Moderate limits for document upload
    limiter.configure("/api/v1/documents", RateLimitConfig(requests=20, window=60))

    # General API limit (from config)
    limiter.configure_default(RateLimitConfig(
        requests=settings.rate_limit_requests,
        window=settings.rate_limit_window_seconds,
    ))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""

    def __init__(self, app, limiter: RateLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter or get_rate_limiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Check rate limit before processing request."""
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/ready", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        allowed, remaining, retry_after = self.limiter.check(request)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                path=request.url.path,
                client=request.client.host if request.client else "unknown",
                retry_after=retry_after,
            )
            raise RateLimitError(retry_after=retry_after)

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


def rate_limit(requests: int = 10, window: int = 60):
    """
    Decorator for applying rate limits to specific endpoints.

    Usage:
        @router.post("/login")
        @rate_limit(requests=5, window=60)
        async def login(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs or args
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                limiter = get_rate_limiter()
                # Use function name as endpoint key for decorator-based limiting
                endpoint_key = f"decorator:{func.__module__}.{func.__name__}"
                limiter.configure(endpoint_key, RateLimitConfig(requests=requests, window=window))

                # Temporarily override path for check
                original_path = request.url.path
                request.scope["path"] = endpoint_key
                allowed, _, retry_after = limiter.check(request)
                request.scope["path"] = original_path

                if not allowed:
                    raise RateLimitError(retry_after=retry_after)

            return await func(*args, **kwargs)

        return wrapper

    return decorator
