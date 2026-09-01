"""
Tests for middleware components.
"""

from github_stars_contrib_mcp.middleware.error_handler import ErrorResponseBuilder
from github_stars_contrib_mcp.middleware.request_context import (
    get_request_duration_ms,
    get_request_id,
    get_user_id,
)


class TestErrorResponseBuilder:
    """Tests for error response builder."""

    def test_validation_error(self):
        """Test validation error response format."""
        response = ErrorResponseBuilder.validation_error("Invalid input")
        assert response["success"] is False
        assert response["data"] is None
        assert "Validation error" in response["error"]

    def test_not_found(self):
        """Test not found error response format."""
        response = ErrorResponseBuilder.not_found("User")
        assert response["success"] is False
        assert "not found" in response["error"]

    def test_server_error(self):
        """Test server error response format."""
        response = ErrorResponseBuilder.server_error("Database connection failed")
        assert response["success"] is False
        assert "Database connection failed" in response["error"]

    def test_permission_denied(self):
        """Test permission denied error response format."""
        response = ErrorResponseBuilder.permission_denied()
        assert response["success"] is False
        assert "Permission denied" in response["error"]

    def test_all_responses_follow_contract(self):
        """Verify all error responses follow standard contract."""
        responses = [
            ErrorResponseBuilder.validation_error("test"),
            ErrorResponseBuilder.not_found("test"),
            ErrorResponseBuilder.server_error(),
            ErrorResponseBuilder.permission_denied(),
        ]

        for response in responses:
            assert "success" in response
            assert response["success"] is False
            assert "data" in response
            assert response["data"] is None
            assert "error" in response
            assert isinstance(response["error"], str)


class TestRequestContext:
    """Tests for request context functions."""

    def test_get_request_id_returns_none_when_not_set(self):
        """Test that request ID returns None when not set."""
        req_id = get_request_id()
        assert req_id is None

    def test_get_user_id_returns_none_when_not_set(self):
        """Test that user ID returns None when not set."""
        user_id = get_user_id()
        assert user_id is None

    def test_get_request_duration_ms_returns_zero_when_not_started(self):
        """Test that request duration returns 0 when start time not set."""
        duration = get_request_duration_ms()
        assert duration == 0.0
