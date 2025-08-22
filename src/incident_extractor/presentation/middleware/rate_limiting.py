"""Rate limiting middleware for API protection."""

import time
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

logger = get_logger(__name__)


class TokenBucket:
    """Token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket."""
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket."""
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait for tokens to be available."""
        self._refill()
        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class RateLimitStore:
    """In-memory rate limit store using token buckets."""

    def __init__(self):
        """Initialize rate limit store."""
        self._buckets: dict[str, TokenBucket] = {}
        self._last_cleanup = time.time()

    def get_bucket(self, key: str, capacity: int, refill_rate: float) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        self._cleanup_expired_buckets()

        if key not in self._buckets:
            self._buckets[key] = TokenBucket(capacity, refill_rate)

        return self._buckets[key]

    def _cleanup_expired_buckets(self) -> None:
        """Clean up expired buckets to prevent memory leaks."""
        now = time.time()

        # Only cleanup every 5 minutes
        if now - self._last_cleanup < 300:
            return

        # Remove buckets that haven't been used in the last hour
        expired_keys = [key for key, bucket in self._buckets.items() if now - bucket.last_refill > 3600]

        for key in expired_keys:
            del self._buckets[key]

        self._last_cleanup = now

        if expired_keys:
            logger.debug("rate_limit_cleanup", cleaned_buckets=len(expired_keys))


# Global rate limit store
rate_limit_store = RateLimitStore()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for API rate limiting using token bucket algorithm."""

    def __init__(
        self,
        app,
        default_requests_per_second: float = 10.0,
        default_burst_capacity: int = 20,
        enabled: bool = True,
        exempt_paths: set[str] | None = None,
    ):
        """Initialize rate limiting middleware."""
        super().__init__(app)
        self.default_rps = default_requests_per_second
        self.default_capacity = default_burst_capacity
        self.enabled = enabled
        self.exempt_paths = exempt_paths or {"/health", "/metrics"}
        self.store = rate_limit_store

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to the request."""
        # Skip rate limiting if disabled or path is exempt
        if not self.enabled or request.url.path in self.exempt_paths:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)

        # Get rate limit parameters
        rps, capacity = await self._get_rate_limit_params(request)

        # Get or create token bucket for this client
        bucket = self.store.get_bucket(client_ip, capacity, rps)

        # Try to consume a token
        if not bucket.consume():
            await self._handle_rate_limit_exceeded(request, bucket)

        # Add rate limit headers to response
        response = await call_next(request)
        self._add_rate_limit_headers(response, bucket, capacity, rps)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"

    async def _get_rate_limit_params(self, request: Request) -> tuple[float, int]:
        """Get rate limit parameters for the request."""
        # For now, return default limits
        return self.default_rps, self.default_capacity

    async def _handle_rate_limit_exceeded(self, request: Request, bucket: TokenBucket) -> None:
        """Handle rate limit exceeded scenario."""
        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = self._get_client_ip(request)
        wait_time = bucket.get_wait_time()

        logger.warning(
            "rate_limit_exceeded",
            request_id=request_id,
            client_ip=client_ip,
            path=request.url.path,
            wait_time_seconds=wait_time,
        )

        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after_seconds": int(wait_time) + 1,
            },
            headers={"Retry-After": str(int(wait_time) + 1)},
        )

    def _add_rate_limit_headers(self, response: Response, bucket: TokenBucket, capacity: int, rps: float) -> None:
        """Add rate limit information to response headers."""
        response.headers["X-RateLimit-Limit"] = str(int(rps))
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + (capacity - bucket.tokens) / rps))
