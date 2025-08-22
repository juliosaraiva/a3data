"""API v1 router configuration."""

from fastapi import APIRouter

from .endpoints import admin, auth, health, incidents

# Create v1 API router
v1_router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)

# Include all endpoint routers
v1_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
v1_router.include_router(health.router, prefix="/health", tags=["health"])
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])

__all__ = [
    "v1_router",
]
