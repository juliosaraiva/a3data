"""Request ID middleware for generating correlation IDs."""

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and track request correlation IDs.

    This middleware generates a unique UUID4 for each request and attaches it to:
    - Request state for use in logging and processing
    - Response headers for client tracking
    - Context variables for structured logging
    """

    def __init__(self, app, header_name: str = "X-Request-ID"):
        """Initialize the middleware.

        Args:
            app: FastAPI application instance
            header_name: Name of the header to use for the request ID
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Generate a unique request ID and add it to the request context.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain

        Returns:
            Response with request ID in headers
        """
        # Check if request ID already exists (from load balancer, etc.)
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())

        # Store in request state for access throughout the request lifecycle
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers for client correlation
        response.headers[self.header_name] = request_id

        return response
