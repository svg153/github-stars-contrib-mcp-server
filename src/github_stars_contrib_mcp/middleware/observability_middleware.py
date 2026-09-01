"""
Phase 3 Observability Middleware for MCP tools.

Provides automatic metrics recording and observability for all tool executions.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import structlog

from ..observability import MetricsCollector, get_tracer
from ..resilience import circuit_breaker_registry

logger = structlog.get_logger(__name__)


class ObservabilityMiddleware:
    """
    Middleware that records metrics and tracing for all tool executions.

    Automatically:
    - Creates tracing spans
    - Records request metrics
    - Tracks errors
    - Monitors circuit breaker state
    """

    def __init__(self, tool_name: str, endpoint: str = "/tools"):
        """
        Initialize middleware.

        Args:
            tool_name: Name of the tool
            endpoint: MCP endpoint (e.g., /tools, /contributions)
        """
        self.tool_name = tool_name
        self.endpoint = endpoint
        self.tracer = get_tracer()

    def __call__(self, func: Callable) -> Callable:
        """Decorate a tool function with observability."""

        async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            start_time = time.monotonic()
            span_name = f"tool_{self.tool_name}"

            with self.tracer.span(span_name, {"tool": self.tool_name}) as span:
                try:
                    # Execute tool
                    result = await func(*args, **kwargs)
                    duration_sec = time.monotonic() - start_time

                    # Record success metrics
                    status = 200 if result.get("success") else 400
                    MetricsCollector.record_request(
                        method="TOOL",
                        endpoint=self.endpoint,
                        status=status,
                        latency_sec=duration_sec,
                    )

                    # Add success event
                    self.tracer.add_event(
                        span,
                        "tool_success",
                        {
                            "tool": self.tool_name,
                            "duration_ms": int(duration_sec * 1000),
                        },
                    )

                    logger.info(
                        "tool_executed",
                        tool=self.tool_name,
                        duration_ms=int(duration_sec * 1000),
                        success=result.get("success"),
                    )

                    return result

                except Exception as e:
                    duration_sec = time.monotonic() - start_time

                    # Record error metrics
                    MetricsCollector.record_request(
                        method="TOOL",
                        endpoint=self.endpoint,
                        status=500,
                        latency_sec=duration_sec,
                    )
                    MetricsCollector.record_error(
                        type(e).__name__,
                        self.endpoint,
                    )

                    # Add error event
                    self.tracer.add_event(
                        span,
                        "error",
                        {
                            "error": str(e),
                            "type": type(e).__name__,
                        },
                    )

                    logger.error(
                        "tool_failed",
                        tool=self.tool_name,
                        error=str(e),
                        error_type=type(e).__name__,
                        duration_ms=int(duration_sec * 1000),
                    )

                    # Update circuit breaker state
                    states = circuit_breaker_registry.get_all_states()
                    for name, state in states.items():
                        MetricsCollector.update_circuit_breaker_state(
                            name,
                            {"closed": 0, "open": 1, "half_open": 2}[state["state"]],
                            state["failure_count"],
                        )

                    raise

        return wrapper


def observe_tool(tool_name: str, endpoint: str = "/tools") -> Callable:
    """
    Decorator for tool functions to add observability.

    Usage:
        @observe_tool("create_contributions", "/contributions")
        async def create_contributions_impl(...):
            ...

    Args:
        tool_name: Name of the tool
        endpoint: MCP endpoint

    Returns:
        Decorated function with observability
    """

    def decorator(func: Callable) -> Callable:
        middleware = ObservabilityMiddleware(tool_name, endpoint)
        return middleware(func)

    return decorator


class CircuitBreakerMonitor:
    """Monitor circuit breaker state changes."""

    def __init__(self):
        """Initialize monitor."""
        self.last_states: dict[str, str] = {}

    def check_and_report(self) -> dict[str, Any]:
        """Check circuit breaker states and report changes."""
        current_states = circuit_breaker_registry.get_all_states()
        changes = {}

        for name, state in current_states.items():
            current_state = state["state"]
            last_state = self.last_states.get(name)

            if current_state != last_state:
                changes[name] = {
                    "from": last_state,
                    "to": current_state,
                    "failures": state["failure_count"],
                }
                logger.warning(
                    "circuit_breaker_state_changed",
                    breaker=name,
                    from_state=last_state,
                    to_state=current_state,
                    failures=state["failure_count"],
                )
                self.last_states[name] = current_state

        if changes:
            MetricsCollector.update_circuit_breaker_state(
                "global",
                len(current_states),
                sum(s["failure_count"] for s in current_states.values()),
            )

        return changes

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        states = circuit_breaker_registry.get_all_states()
        return {
            "total_breakers": len(states),
            "open_count": sum(1 for s in states.values() if s["state"] == "open"),
            "closed_count": sum(1 for s in states.values() if s["state"] == "closed"),
            "half_open_count": sum(
                1 for s in states.values() if s["state"] == "half_open"
            ),
            "total_failures": sum(s["failure_count"] for s in states.values()),
        }


# Global circuit breaker monitor
_cb_monitor = CircuitBreakerMonitor()


def get_circuit_breaker_monitor() -> CircuitBreakerMonitor:
    """Get global circuit breaker monitor."""
    return _cb_monitor
