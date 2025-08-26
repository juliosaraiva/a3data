"""
Error handling integration tests for the Incident Extractor API.

This module tests various error scenarios and edge cases to ensure
robust error handling and proper response codes.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling scenarios."""

    def test_empty_text_validation(self, client: TestClient):
        """Test validation error for empty text."""
        request_data = {"text": ""}

        response = client.post("/api/v1/incidents/extract", json=request_data)

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_text_too_short_validation(self, client: TestClient):
        """Test validation error for text that's too short."""
        request_data = {"text": "Short"}  # Less than 10 chars

        response = client.post("/api/v1/incidents/extract", json=request_data)

        assert response.status_code == 422

    def test_text_too_long_validation(self, client: TestClient):
        """Test validation error for text that's too long."""
        request_data = {"text": "X" * 5001}  # Over 5000 chars

        response = client.post("/api/v1/incidents/extract", json=request_data)

        assert response.status_code == 422

    def test_missing_text_field(self, client: TestClient):
        """Test error when text field is missing."""
        request_data = {"wrong_field": "some content"}

        response = client.post("/api/v1/incidents/extract", json=request_data)

        assert response.status_code == 422

    def test_invalid_json_format(self, client: TestClient):
        """Test error handling for invalid JSON."""
        response = client.post(
            "/api/v1/incidents/extract", data="invalid json content", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_wrong_content_type(self, client: TestClient):
        """Test error handling for wrong content type."""
        response = client.post(
            "/api/v1/incidents/extract",
            data="text=some incident text",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Should still work or return appropriate error
        assert response.status_code in [200, 422, 415]

    def test_nonexistent_endpoint(self, client: TestClient):
        """Test 404 for nonexistent endpoints."""
        response = client.post("/api/v1/incidents/nonexistent")

        assert response.status_code == 404

    def test_wrong_http_method(self, client: TestClient):
        """Test error for wrong HTTP method."""
        response = client.get("/api/v1/incidents/extract")

        assert response.status_code == 405  # Method Not Allowed
