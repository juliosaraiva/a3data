"""
FastAPI routers module.

This module contains API routers for different endpoint groups including
health checks, extraction, metrics, and debug endpoints.

All routers are properly organized with:
- Health router: System health monitoring and status validation
- Extraction router: Core incident extraction functionality
- Metrics router: Application performance and monitoring metrics
- Debug router: Development and debugging endpoints with system introspection
"""

# Import all router modules
from . import debug, extraction, health, metrics

# Export all routers for application integration
__all__ = [
    "health",
    "extraction",
    "metrics",
    "debug",
]
