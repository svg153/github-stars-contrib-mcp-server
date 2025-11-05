"""MCP resource for Prometheus metrics endpoint."""

from __future__ import annotations

import structlog

from ..observability import get_metrics
from ..resilience import circuit_breaker_registry
from ..shared import mcp

logger = structlog.get_logger(__name__)


@mcp.resource(uri="metrics://prometheus")
async def get_prometheus_metrics() -> str:
    """
    Get Prometheus metrics in text format.

    Returns:
        Prometheus-formatted metrics string
    """
    metrics_bytes = get_metrics()

    # Add circuit breaker states as comments
    cb_states = circuit_breaker_registry.get_all_states()
    metrics_text = metrics_bytes.decode("utf-8")

    if cb_states:
        metrics_text += "\n# Circuit Breaker States\n"
        for name, state in cb_states.items():
            metrics_text += (
                f"# {name}: {state['state']} (failures: {state['failure_count']})\n"
            )

    return metrics_text
