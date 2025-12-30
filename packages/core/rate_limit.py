"""Rate limiting middleware for Airport API.

Supports both in-memory (development) and Redis-based (production) rate limiting.
Includes IP validation and fail-secure modes for auth endpoints.
"""

import ipaddress
import re
import time
from abc import ABC, abstractmethod
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
    # If True, fail closed (deny) when rate limiter is unavailable
    # Set to True for auth endpoints to prevent brute force attacks
    fail_closed: bool = False


@dataclass
class RateLimitEntry:
    """Track request counts for a client."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


def _validate_ip(ip_string: str) -> str | None:
    """
    Validate and normalize an IP address string.

    Returns the normalized IP if valid, None otherwise.
    Prevents IP spoofing via malformed X-Forwarded-For headers.
    """
    if not ip_string:
        return None

    # Remove any port numbers
    ip_string = ip_string.strip()
    if ip_string.startswith("["):
        # IPv6 with port [::1]:8080
        match = re.match(r'\[([^\]]+)\](?::\d+)?', ip_string)
        if match:
            ip_string = match.group(1)
    elif ":" in ip_string and ip_string.count(":") == 1:
        # IPv4 with port 127.0.0.1:8080
        ip_string = ip_string.rsplit(":", 1)[0]

    try:
        # Validate and normalize
        ip_obj = ipaddress.ip_address(ip_string)
        return str(ip_obj)
    except ValueError:
        return None


def _get_trusted_client_ip(request: Request) -> str:
    """
    Get client IP with proper X-Forwarded-For handling.

    - Only trusts X-Forwarded-For if there's a direct client IP
    - Validates IP format to prevent spoofing
    - Falls back to direct client IP if header is invalid
    """
    # Get direct client IP first
    direct_ip = request.client.host if request.client else None
    if not direct_ip:
        return "unknown"

    # Check for forwarded header
    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return _validate_ip(direct_ip) or "unknown"

    # Parse X-Forwarded-For (rightmost is most trusted if behind load balancer)
    # Format: client, proxy1, proxy2
    # We take the first (leftmost) as that's the original client
    # But we validate it's a proper IP
    parts = [p.strip() for p in forwarded.split(",")]

    for part in parts:
        validated_ip = _validate_ip(part)
        if validated_ip:
            return validated_ip

    # If all forwarded IPs are invalid, use direct connection
    logger.warning(
        "rate_limit_invalid_forwarded_for",
        header=forwarded,
        direct_ip=direct_ip,
    )
    return _validate_ip(direct_ip) or "unknown"


class BaseRateLimiter(ABC):
    """Abstract base class for rate limiters."""

    def __init__(self) -> None:
        self._configs: dict[str, RateLimitConfig] = {}
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

        # Use validated IP address (NEW-007 fix)
        client_ip = _get_trusted_client_ip(request)
        return f"{client_ip}:{request.url.path}"

    @abstractmethod
    def check(self, request: Request) -> tuple[bool, int, int]:
        """
        Check if request is allowed.

        Returns:
            tuple: (allowed, remaining, retry_after)
        """
        pass

    @abstractmethod
    def reset(self, client_key: str) -> None:
        """Reset rate limit for a client."""
        pass


class InMemoryRateLimiter(BaseRateLimiter):
    """
    In-memory rate limiter using sliding window algorithm.

    For development only - does not work across multiple instances.
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

    def check(self, request: Request) -> tuple[bool, int, int]:
        """Check if request is allowed."""
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


class RedisRateLimiter(BaseRateLimiter):
    """
    Redis-based rate limiter for production multi-instance deployments.

    Uses Redis INCR with expiry for atomic, distributed rate limiting.
    This implementation works correctly across multiple API instances.

    Supports fail_closed mode for auth endpoints to prevent brute force
    attacks when Redis is unavailable.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        super().__init__()
        self._redis_url = redis_url or settings.redis_url
        self._redis = None
        self._key_prefix = "ratelimit:"
        self._redis_available = True
        self._last_redis_check = 0.0
        self._redis_check_interval = 30.0  # Retry Redis connection every 30s

    def _get_redis(self):
        """Lazy initialization of Redis connection with health checking."""
        now = time.time()

        # If Redis was unavailable, periodically retry
        if not self._redis_available:
            if now - self._last_redis_check < self._redis_check_interval:
                return None
            self._last_redis_check = now

        if self._redis is None or not self._redis_available:
            try:
                import redis
                self._redis = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    retry_on_timeout=False,
                )
                # Test connection
                self._redis.ping()
                self._redis_available = True
                logger.info("rate_limiter_redis_connected", url=self._redis_url.split("@")[-1])
            except Exception as e:
                self._redis_available = False
                self._last_redis_check = now
                logger.warning(
                    "rate_limiter_redis_unavailable",
                    error=str(e),
                )
                return None
        return self._redis

    def check(self, request: Request) -> tuple[bool, int, int]:
        """
        Check if request is allowed using Redis.

        For auth endpoints (fail_closed=True), denies requests when Redis
        is unavailable to prevent brute force attacks.
        """
        endpoint = request.url.path
        config = self._get_config(endpoint)
        client_key = self._get_client_key(request, config)
        redis_key = f"{self._key_prefix}{client_key}"

        redis_client = self._get_redis()

        if redis_client is None:
            # NEW-006 fix: Check fail_closed setting
            if config.fail_closed:
                logger.warning(
                    "rate_limiter_redis_unavailable_deny",
                    endpoint=endpoint,
                    action="denying_request",
                    reason="fail_closed mode for auth endpoint",
                )
                # Deny request with 60 second retry when Redis is down for auth
                return False, 0, 60
            else:
                # For non-auth endpoints, allow with warning
                logger.warning(
                    "rate_limiter_redis_unavailable_allow",
                    endpoint=endpoint,
                    action="allowing_request",
                )
                return True, config.requests - 1, 0

        try:
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()

            # Get current count and TTL
            pipe.incr(redis_key)
            pipe.ttl(redis_key)
            results = pipe.execute()

            current_count = results[0]
            ttl = results[1]

            # Set expiry if this is the first request in the window
            if ttl == -1:  # Key exists but has no expiry (shouldn't happen, but handle it)
                redis_client.expire(redis_key, config.window)
                ttl = config.window
            elif current_count == 1:  # First request in window
                redis_client.expire(redis_key, config.window)
                ttl = config.window

            # Check if over limit
            if current_count > config.requests:
                retry_after = max(1, ttl if ttl > 0 else config.window)
                return False, 0, retry_after

            remaining = config.requests - current_count
            return True, remaining, 0

        except Exception as e:
            self._redis_available = False
            self._last_redis_check = time.time()

            # Check fail_closed on error too
            if config.fail_closed:
                logger.error(
                    "rate_limiter_redis_error_deny",
                    error=str(e),
                    endpoint=endpoint,
                    action="denying_request",
                )
                return False, 0, 60
            else:
                logger.warning(
                    "rate_limiter_redis_error_allow",
                    error=str(e),
                    endpoint=endpoint,
                    action="allowing_request",
                )
                return True, config.requests - 1, 0

    def reset(self, client_key: str) -> None:
        """Reset rate limit for a client in Redis."""
        redis_client = self._get_redis()
        if redis_client:
            try:
                redis_key = f"{self._key_prefix}{client_key}"
                redis_client.delete(redis_key)
            except Exception as e:
                logger.warning("rate_limiter_reset_error", error=str(e))


# Type alias for backward compatibility
RateLimiter = InMemoryRateLimiter


# Global rate limiter instance
_rate_limiter: BaseRateLimiter | None = None


def get_rate_limiter() -> BaseRateLimiter:
    """
    Get the global rate limiter instance.

    Uses Redis in production, in-memory for development.
    """
    global _rate_limiter
    if _rate_limiter is None:
        # Use Redis for production, in-memory for development
        if settings.environment == "production":
            _rate_limiter = RedisRateLimiter()
            logger.info("rate_limiter_initialized", type="redis")
        else:
            _rate_limiter = InMemoryRateLimiter()
            logger.info("rate_limiter_initialized", type="in-memory")
        _configure_default_limits(_rate_limiter)
    return _rate_limiter


def _configure_default_limits(limiter: BaseRateLimiter) -> None:
    """Configure default rate limits for sensitive endpoints."""
    # Strict limits for auth endpoints (from config) - fail closed!
    auth_config = RateLimitConfig(
        requests=settings.rate_limit_auth_requests,
        window=settings.rate_limit_auth_window_seconds,
        fail_closed=True,  # Deny when Redis is down
    )
    limiter.configure("/api/v1/auth/login", auth_config)
    limiter.configure("/api/v1/auth/register", auth_config)
    limiter.configure("/api/v1/auth/forgot-password", RateLimitConfig(
        requests=3,
        window=300,
        fail_closed=True,
    ))
    limiter.configure("/api/v1/auth/reset-password", RateLimitConfig(
        requests=5,
        window=300,
        fail_closed=True,
    ))

    # Rate limit for read operations (NEW-022 fix)
    # More generous but still prevents scraping
    read_config = RateLimitConfig(requests=200, window=60)
    limiter.configure("/api/v1/transactions", read_config)
    limiter.configure("/api/v1/documents", read_config)
    limiter.configure("/api/v1/deadlines", read_config)

    # Moderate limits for document upload
    limiter.configure("/api/v1/documents/upload", RateLimitConfig(requests=20, window=60))

    # General API limit (from config)
    limiter.configure_default(RateLimitConfig(
        requests=settings.rate_limit_requests,
        window=settings.rate_limit_window_seconds,
    ))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""

    def __init__(self, app, limiter: BaseRateLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter or get_rate_limiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Check rate limit before processing request."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ("/health", "/ready", "/live", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        allowed, remaining, retry_after = self.limiter.check(request)

        if not allowed:
            client_ip = _get_trusted_client_ip(request)
            logger.warning(
                "rate_limit_exceeded",
                path=request.url.path,
                client_ip=client_ip,
                retry_after=retry_after,
            )
            raise RateLimitError(retry_after=retry_after)

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


def rate_limit(requests: int = 10, window: int = 60, fail_closed: bool = False):
    """
    Decorator for applying rate limits to specific endpoints.

    Args:
        requests: Number of requests allowed per window
        window: Window size in seconds
        fail_closed: If True, deny requests when rate limiter is unavailable

    Usage:
        @router.post("/login")
        @rate_limit(requests=5, window=60, fail_closed=True)
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
                limiter.configure(endpoint_key, RateLimitConfig(
                    requests=requests,
                    window=window,
                    fail_closed=fail_closed,
                ))

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
