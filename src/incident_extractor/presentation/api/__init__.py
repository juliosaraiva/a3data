"""API router configuration for the incident extraction system."""

from .v1 import v1_router

__all__ = [
    "v1_router",
]

# Main API router that includes all versions
api_router = v1_router
