"""Authentication and authorization middleware."""

from collections.abc import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

logger = get_logger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling authentication and authorization."""

    def __init__(
        self,
        app,
        secret_key: str = "dev-secret-key",
        exempt_paths: set[str] | None = None,
        enabled: bool = True,
    ):
        """Initialize authentication middleware."""
        super().__init__(app)
        self.secret_key = secret_key
        self.exempt_paths = exempt_paths or {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
        }
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate authentication for the request."""
        # Skip authentication if disabled or path is exempt
        if not self.enabled or request.url.path in self.exempt_paths:
            return await call_next(request)

        # Extract authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return await self._handle_missing_auth(request)

        try:
            # Parse authorization header
            if not auth_header.startswith("Bearer "):
                return await self._handle_invalid_auth(request, "Invalid auth format")

            token = auth_header.split(" ")[1]

            # Validate token (placeholder implementation)
            user_context = await self._validate_token(token)

            # Set user context in request state
            request.state.user = user_context
            request.state.authenticated = True

            return await call_next(request)

        except Exception as exc:
            return await self._handle_auth_error(request, exc)

    async def _validate_token(self, token: str) -> dict:
        """Validate JWT token and return user context."""
        # Placeholder - accept any non-empty token as valid
        if token == "invalid-token":
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "user_id": "user-123",
            "email": "user@example.com",
            "roles": ["user"],
            "permissions": ["read:incidents", "write:incidents"],
        }

    async def _handle_missing_auth(self, request: Request) -> HTTPException:
        """Handle missing authentication."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            "authentication_missing",
            request_id=request_id,
            path=request.url.path,
        )

        raise HTTPException(
            status_code=401,
            detail={
                "error": "Authentication required",
                "message": "Please provide a valid authorization token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def _handle_invalid_auth(self, request: Request, reason: str) -> HTTPException:
        """Handle invalid authentication format."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            "authentication_invalid_format",
            request_id=request_id,
            path=request.url.path,
            reason=reason,
        )

        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid authentication format",
                "message": "Authorization header must be in 'Bearer <token>' format",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def _handle_auth_error(self, request: Request, exc: Exception) -> HTTPException:
        """Handle authentication errors."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            "authentication_error",
            request_id=request_id,
            path=request.url.path,
            error=str(exc),
            error_type=exc.__class__.__name__,
        )

        if isinstance(exc, HTTPException):
            raise exc

        raise HTTPException(
            status_code=401,
            detail={
                "error": "Authentication failed",
                "message": "Unable to validate authentication credentials",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
