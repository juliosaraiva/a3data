"""
FastAPI Middleware Layer.

This package provides production-ready middleware components for the FastAPI application,
including error handling, request logging, performance timing, and security features.

The middleware components are designed for:
- Production readability and maintainability
- Clear separation of concerns
- Clean, modular architecture
- Comprehensive logging and monitoring

Middleware Components:
- error_handling: Global exception handling with standardized responses
- logging: Structured request/response logging with correlation IDs
- timing: Request performance monitoring and metrics collection
- security: Security headers and request validation
- cors: CORS configuration with environment-specific settings

Usage:
    from .error_handling import ErrorHandlingMiddleware
    from .logging import RequestLoggingMiddleware
    from .timing import TimingMiddleware
    from .security import SecurityMiddleware
    from .cors import CORSConfiguration, configure_cors
"""

# Import middleware components for easy access
from .cors import CORSConfiguration, configure_cors
from .error_handling import ErrorHandlingMiddleware
from .logging import RequestLoggingMiddleware
from .security import SecurityMiddleware
from .timing import TimingMiddleware

__all__ = [
    "ErrorHandlingMiddleware",
    "RequestLoggingMiddleware",
    "TimingMiddleware",
    "SecurityMiddleware",
    "CORSConfiguration",
    "configure_cors",
]
