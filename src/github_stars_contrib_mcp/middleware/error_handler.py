"""ASGI error handling helpers with the standard MCP tool response contract."""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ErrorHandlerMiddleware:
    """Catch uncaught HTTP exceptions and return a structured JSON response."""

    def __init__(self, app: Any, log_level: str = "error") -> None:
        self.app = app
        self.log_level = log_level

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                status = int(message.get("status", 500))
                if status >= 400:
                    logger.warning(
                        "http_error_response",
                        status_code=status,
                        path=scope.get("path"),
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            self._log_exception(exc, scope)
            await self._send_error_response(send, exc)

    def _log_exception(self, exc: Exception, scope: dict[str, Any]) -> None:
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
    async def _send_error_response(send: Any, exc: Exception) -> None:
        status = 500
        if isinstance(exc, ValueError):
            status = 400
        elif isinstance(exc, PermissionError):
            status = 403
        elif isinstance(exc, FileNotFoundError):
            status = 404
        elif isinstance(exc, TimeoutError):
            status = 504

        body = json.dumps({"success": False, "data": None, "error": str(exc)}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    @staticmethod
    def _get_client_ip(scope: dict[str, Any]) -> str:
        client = scope.get("client")
        return str(client[0]) if client else "unknown"


class ErrorResponseBuilder:
    """Factory for the response contract used by MCP tools."""

    @staticmethod
    def validation_error(message: str) -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": f"Validation error: {message}",
        }

    @staticmethod
    def not_found(resource: str) -> dict[str, Any]:
        return {"success": False, "data": None, "error": f"{resource} not found"}

    @staticmethod
    def server_error(message: str = "Internal server error") -> dict[str, Any]:
        return {"success": False, "data": None, "error": message}

    @staticmethod
    def permission_denied(message: str = "Permission denied") -> dict[str, Any]:
        return {"success": False, "data": None, "error": message}
