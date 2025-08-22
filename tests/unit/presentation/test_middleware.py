"""Test the middleware stack implementation."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.incident_extractor.core.config.config import Environment, Settings
from src.incident_extractor.presentation.middleware import setup_middleware


def test_middleware_setup():
    """Test that middleware can be set up without errors."""
    app = FastAPI()
    settings = Settings()

    # This should not raise any exceptions
    setup_middleware(app, settings)

    # Check that middleware has been added to the app
    assert len(app.user_middleware) > 0


def test_middleware_stack_integration():
    """Test that the complete middleware stack works together."""
    app = FastAPI()

    # Add a simple endpoint for testing
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test successful"}

    # Set up middleware with development settings
    settings = Settings(environment=Environment.DEVELOPMENT)
    setup_middleware(app, settings)

    # Create test client
    client = TestClient(app)

    # Make a request - should pass through all middleware
    response = client.get("/test")

    assert response.status_code == 200
    assert response.json() == {"message": "test successful"}

    # Check that request ID header is added
    assert "X-Request-ID" in response.headers


def test_health_endpoint_bypasses_auth():
    """Test that health endpoints bypass authentication."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    # Set up middleware with production settings (auth enabled)
    settings = Settings(environment=Environment.PRODUCTION)
    setup_middleware(app, settings)

    client = TestClient(app)

    # Health endpoint should work without authentication
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


if __name__ == "__main__":
    pytest.main([__file__])
