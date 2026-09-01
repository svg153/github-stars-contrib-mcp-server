"""
Request context middleware for capturing and propagating request metadata.
"""

import time
import uuid
from contextvars import ContextVar

import structlog

logger = structlog.get_logger(__name__)

# Context variables for request scoping
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
start_time_var: ContextVar[float | None] = ContextVar("start_time", default=None)


class RequestContextMiddleware:
    """
    Middleware to capture request context (ID, user, timing) for logging.
    Use with FastMCP or similar frameworks.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """ASGI middleware handler."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate unique request ID
        req_id = str(uuid.uuid4())
        request_id_var.set(req_id)

        # Start timing
        start_time_var.set(time.time())

        # Extract user ID from Authorization header if present
        user_id = self._extract_user_id(scope)
        user_id_var.set(user_id)

        # Log request start
        logger.info(
            "request_started",
            request_id=req_id,
            method=scope.get("method"),
            path=scope.get("path"),
            user_id=user_id,
            client_ip=self._get_client_ip(scope),
        )

        try:
            await self.app(scope, receive, send)
        except Exception as e:
            logger.error(
                "request_error",
                request_id=req_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    @staticmethod
    def _extract_user_id(scope) -> str | None:
        """Extract user ID from Authorization header."""
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        if auth_header.startswith("Bearer "):
            # Extract token (in real app, would decode JWT)
            token = auth_header[7:]
            return f"user_{hash(token) % 10000}"
        return None

    @staticmethod
    def _get_client_ip(scope) -> str | None:
        """Get client IP address."""
        client = scope.get("client")
        return client[0] if client else None


def get_request_id() -> str | None:
    """Get current request ID from context."""
    return request_id_var.get()


def get_user_id() -> str | None:
    """Get current user ID from context."""
    return user_id_var.get()


def get_request_duration_ms() -> float:
    """Get elapsed time since request started (in milliseconds)."""
    start = start_time_var.get()
    if start is None:
        return 0.0
    return (time.time() - start) * 1000
