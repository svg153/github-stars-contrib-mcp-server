"""
Prometheus metrics for observability.
Tracks requests, latency, errors, and circuit breaker states.
"""

import structlog
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = structlog.get_logger(__name__)

# Create default registry
DEFAULT_REGISTRY = CollectorRegistry()

# Request metrics
REQUEST_COUNT = Counter(
    "mcp_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status"],
    registry=DEFAULT_REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "mcp_request_latency_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
    registry=DEFAULT_REGISTRY,
)

REQUEST_SIZE = Histogram(
    "mcp_request_size_bytes",
    "API request size in bytes",
    ["method", "endpoint"],
    registry=DEFAULT_REGISTRY,
)

RESPONSE_SIZE = Histogram(
    "mcp_response_size_bytes",
    "API response size in bytes",
    ["method", "endpoint"],
    registry=DEFAULT_REGISTRY,
)

# Error metrics
ERROR_COUNT = Counter(
    "mcp_errors_total",
    "Total number of errors",
    ["error_type", "endpoint"],
    registry=DEFAULT_REGISTRY,
)

RETRY_COUNT = Counter(
    "mcp_retries_total",
    "Total number of retries",
    ["endpoint", "attempt"],
    registry=DEFAULT_REGISTRY,
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "mcp_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["name"],
    registry=DEFAULT_REGISTRY,
)

CIRCUIT_BREAKER_FAILURES = Gauge(
    "mcp_circuit_breaker_failures",
    "Current failure count in circuit breaker",
    ["name"],
    registry=DEFAULT_REGISTRY,
)

# Contribution metrics
CONTRIBUTIONS_CREATED = Counter(
    "mcp_contributions_created_total",
    "Total contributions created",
    ["type"],
    registry=DEFAULT_REGISTRY,
)

CONTRIBUTIONS_UPDATED = Counter(
    "mcp_contributions_updated_total",
    "Total contributions updated",
    ["type"],
    registry=DEFAULT_REGISTRY,
)

CONTRIBUTIONS_DELETED = Counter(
    "mcp_contributions_deleted_total",
    "Total contributions deleted",
    registry=DEFAULT_REGISTRY,
)

# Cache metrics
CACHE_HITS = Counter(
    "mcp_cache_hits_total",
    "Total cache hits",
    ["cache_type"],
    registry=DEFAULT_REGISTRY,
)

CACHE_MISSES = Counter(
    "mcp_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
    registry=DEFAULT_REGISTRY,
)

CACHE_SIZE = Gauge(
    "mcp_cache_size_bytes",
    "Current cache size in bytes",
    ["cache_type"],
    registry=DEFAULT_REGISTRY,
)


class MetricsCollector:
    """Convenience class for recording metrics."""

    @staticmethod
    def record_request(
        method: str,
        endpoint: str,
        status: int,
        latency_sec: float,
        req_size: int = 0,
        resp_size: int = 0,
    ):
        """Record API request metrics."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency_sec)
        if req_size > 0:
            REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(req_size)
        if resp_size > 0:
            RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(resp_size)

    @staticmethod
    def record_error(error_type: str, endpoint: str):
        """Record error occurrence."""
        ERROR_COUNT.labels(error_type=error_type, endpoint=endpoint).inc()

    @staticmethod
    def record_retry(endpoint: str, attempt: int):
        """Record retry attempt."""
        RETRY_COUNT.labels(endpoint=endpoint, attempt=attempt).inc()

    @staticmethod
    def update_circuit_breaker_state(name: str, state: int, failures: int):
        """Update circuit breaker state (0=closed, 1=open, 2=half_open)."""
        CIRCUIT_BREAKER_STATE.labels(name=name).set(state)
        CIRCUIT_BREAKER_FAILURES.labels(name=name).set(failures)

    @staticmethod
    def record_contribution_created(contrib_type: str):
        """Record contribution creation."""
        CONTRIBUTIONS_CREATED.labels(type=contrib_type).inc()

    @staticmethod
    def record_contribution_updated(contrib_type: str):
        """Record contribution update."""
        CONTRIBUTIONS_UPDATED.labels(type=contrib_type).inc()

    @staticmethod
    def record_contribution_deleted():
        """Record contribution deletion."""
        CONTRIBUTIONS_DELETED.inc()

    @staticmethod
    def record_cache_hit(cache_type: str):
        """Record cache hit."""
        CACHE_HITS.labels(cache_type=cache_type).inc()

    @staticmethod
    def record_cache_miss(cache_type: str):
        """Record cache miss."""
        CACHE_MISSES.labels(cache_type=cache_type).inc()

    @staticmethod
    def set_cache_size(cache_type: str, size_bytes: int):
        """Set cache size."""
        CACHE_SIZE.labels(cache_type=cache_type).set(size_bytes)


def get_metrics() -> bytes:
    """Get all metrics in Prometheus format."""
    return generate_latest(DEFAULT_REGISTRY)
