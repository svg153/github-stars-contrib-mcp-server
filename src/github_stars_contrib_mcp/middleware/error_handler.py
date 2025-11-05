"""
Error handling middleware with structured error responses.
"""

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Standard error response contract: {success, data, error}
ERROR_RESPONSE_CONTRACT = {
    "success": False,
    "data": None,
    "error": str,
}


class ErrorHandlerMiddleware:
    """
    Middleware to catch exceptions and return structured error responses.
    Logs errors with context and converts to standard response format.
    """

    def __init__(self, app, log_level: str = "error"):
        self.app = app
        self.log_level = log_level

    async def __call__(self, scope, receive, send):
        """ASGI middleware handler."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            """Wrapper to capture response status."""
            if message["type"] == "http.response.start":
                # Capture status code for logging
                status_code = message.get("status", 500)
                if status_code >= 400:
                    logger.warning(
                        "http_error_response",
                        status_code=status_code,
                        path=scope.get("path"),
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            # Log error with context
            self._log_exception(exc, scope)

            # Send error response
            await self._send_error_response(
                send, exc, scope.get("path"), scope.get("method")
            )

    def _log_exception(self, exc: Exception, scope: dict[str, Any]) -> None:
        """Log exception with context."""
        log_func = getattr(logger, self.log_level)
        log_func(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=scope.get("path"),
            method=scope.get("method"),
            client_ip=self._get_client_ip(scope),
        )

    @staticmethod
    async def _send_error_response(
        send, exc: Exception, path: str, method: str
    ) -> None:
        """Send standardized error response."""
        # Determine HTTP status code based on exception type
        status_code = 500
        if isinstance(exc, ValueError):
            status_code = 400
        elif isinstance(exc, PermissionError):
            status_code = 403
        elif isinstance(exc, FileNotFoundError):
            status_code = 404
        elif isinstance(exc, TimeoutError):
            status_code = 504

        # Build response body
        error_response = {
            "success": False,
            "data": None,
            "error": str(exc),
        }

        response_body = json.dumps(error_response).encode()

        # Send response
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(response_body)).encode()],
            ],
        })

        await send({
            "type": "http.response.body",
            "body": response_body,
        })

    @staticmethod
    def _get_client_ip(scope: dict[str, Any]) -> str:
        """Extract client IP from scope."""
        client = scope.get("client")
        return client[0] if client else "unknown"


class ErrorResponseBuilder:
    """Builder for standardized error responses."""

    @staticmethod
    def validation_error(message: str) -> dict[str, Any]:
        """Build validation error response."""
        return {
            "success": False,
            "data": None,
            "error": f"Validation error: {message}",
        }

    @staticmethod
    def not_found(resource: str) -> dict[str, Any]:
        """Build not found error response."""
        return {
            "success": False,
            "data": None,
            "error": f"{resource} not found",
        }

    @staticmethod
    def server_error(message: str = "Internal server error") -> dict[str, Any]:
        """Build server error response."""
        return {
            "success": False,
            "data": None,
            "error": message,
        }

    @staticmethod
    def permission_denied(message: str = "Permission denied") -> dict[str, Any]:
        """Build permission denied error response."""
        return {
            "success": False,
            "data": None,
            "error": message,
        }
