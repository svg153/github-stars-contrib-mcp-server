"""Prometheus metrics for Stars API and MCP tool observability."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

DEFAULT_REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "mcp_requests_total",
    "Total number of upstream API requests",
    ["method", "endpoint", "status"],
    registry=DEFAULT_REGISTRY,
)
REQUEST_LATENCY = Histogram(
    "mcp_request_latency_seconds",
    "Upstream API request latency in seconds",
    ["method", "endpoint"],
    registry=DEFAULT_REGISTRY,
)
REQUEST_SIZE = Histogram(
    "mcp_request_size_bytes",
    "Upstream request size in bytes",
    ["method", "endpoint"],
    registry=DEFAULT_REGISTRY,
)
RESPONSE_SIZE = Histogram(
    "mcp_response_size_bytes",
    "Upstream response size in bytes",
    ["method", "endpoint"],
    registry=DEFAULT_REGISTRY,
)
ERROR_COUNT = Counter(
    "mcp_errors_total",
    "Total number of upstream errors",
    ["error_type", "endpoint"],
    registry=DEFAULT_REGISTRY,
)
RETRY_COUNT = Counter(
    "mcp_retries_total",
    "Total retry attempts",
    ["endpoint", "attempt"],
    registry=DEFAULT_REGISTRY,
)
CIRCUIT_BREAKER_STATE = Gauge(
    "mcp_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["name"],
    registry=DEFAULT_REGISTRY,
)
CIRCUIT_BREAKER_FAILURES = Gauge(
    "mcp_circuit_breaker_failures",
    "Current failure count in a circuit breaker",
    ["name"],
    registry=DEFAULT_REGISTRY,
)
CONTRIBUTIONS_CREATED = Counter(
    "mcp_contributions_created_total",
    "Total contributions created",
    ["type"],
    registry=DEFAULT_REGISTRY,
)
CONTRIBUTIONS_UPSERTED = Counter(
    "mcp_contributions_upserted_total",
    "Total contribution REST upserts",
    ["type"],
    registry=DEFAULT_REGISTRY,
)
CACHE_HITS = Counter(
    "mcp_cache_hits_total", "Total cache hits", ["cache_type"], registry=DEFAULT_REGISTRY
)
CACHE_MISSES = Counter(
    "mcp_cache_misses_total", "Total cache misses", ["cache_type"], registry=DEFAULT_REGISTRY
)
CACHE_SIZE = Gauge(
    "mcp_cache_size_bytes", "Current cache size in bytes", ["cache_type"], registry=DEFAULT_REGISTRY
)


class MetricsCollector:
    @staticmethod
    def record_request(
        method: str,
        endpoint: str,
        status: int,
        latency_sec: float,
        req_size: int = 0,
        resp_size: int = 0,
    ) -> None:
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency_sec)
        if req_size > 0:
            REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(req_size)
        if resp_size > 0:
            RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(resp_size)

    @staticmethod
    def record_error(error_type: str, endpoint: str) -> None:
        ERROR_COUNT.labels(error_type=error_type, endpoint=endpoint).inc()

    @staticmethod
    def record_retry(endpoint: str, attempt: int) -> None:
        RETRY_COUNT.labels(endpoint=endpoint, attempt=attempt).inc()

    @staticmethod
    def update_circuit_breaker_state(name: str, state: int, failures: int) -> None:
        CIRCUIT_BREAKER_STATE.labels(name=name).set(state)
        CIRCUIT_BREAKER_FAILURES.labels(name=name).set(failures)

    @staticmethod
    def record_contribution_created(contrib_type: str) -> None:
        CONTRIBUTIONS_CREATED.labels(type=contrib_type).inc()

    @staticmethod
    def record_contribution_updated(contrib_type: str) -> None:
        """Compatibility name for the REST upsert metric."""
        CONTRIBUTIONS_UPSERTED.labels(type=contrib_type).inc()

    @staticmethod
    def record_contribution_deleted() -> None:
        """Compatibility no-op: the current Contributions REST API has no DELETE."""

    @staticmethod
    def record_cache_hit(cache_type: str) -> None:
        CACHE_HITS.labels(cache_type=cache_type).inc()

    @staticmethod
    def record_cache_miss(cache_type: str) -> None:
        CACHE_MISSES.labels(cache_type=cache_type).inc()

    @staticmethod
    def set_cache_size(cache_type: str, size_bytes: int) -> None:
        CACHE_SIZE.labels(cache_type=cache_type).set(size_bytes)


def get_metrics() -> bytes:
    return generate_latest(DEFAULT_REGISTRY)
