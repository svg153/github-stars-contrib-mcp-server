"""Integration tests for Phase 3 observability features."""

import pytest

from github_stars_contrib_mcp.observability import (
    MetricsCollector,
    get_metrics,
    get_tracer,
)
from github_stars_contrib_mcp.resilience import (
    CircuitBreakerException,
    circuit_breaker_registry,
)


class TestPhase3Integration:
    """Integration tests for circuit breaker, metrics, and tracing."""

    def test_metrics_collector_integration(self):
        """Test metrics can be collected and exported."""
        # Record various metrics
        MetricsCollector.record_request(
            method="POST",
            endpoint="/contributions",
            status=201,
            latency_sec=0.5,
            req_size=100,
            resp_size=200,
        )
        MetricsCollector.record_contribution_created("LINK")
        MetricsCollector.record_error("HTTP_ERROR", "/contributions")

        # Get metrics
        metrics = get_metrics()
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0

    def test_circuit_breaker_integration(self):
        """Test circuit breaker registry works."""
        breaker = circuit_breaker_registry.get_or_create("test_service")
        assert breaker is not None

        # Get states
        states = circuit_breaker_registry.get_all_states()
        assert "test_service" in states
        assert states["test_service"]["state"] == "closed"

    def test_tracer_integration(self):
        """Test tracer works without errors."""
        tracer = get_tracer()
        assert tracer is not None

        # Use span
        with tracer.span("test_operation", {"id": "123"}) as span:
            tracer.add_event(span, "test_event", {"key": "value"})

        # Should not raise

    def test_circuit_breaker_with_metrics(self):
        """Test circuit breaker and metrics together."""
        breaker = circuit_breaker_registry.get_or_create("api_test")

        call_count = {"count": 0}

        def api_call():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise Exception("API error")
            return "success"

        # First 2 calls fail
        with pytest.raises(Exception):
            breaker.call(api_call)

        with pytest.raises(Exception):
            breaker.call(api_call)

        # Circuit should be open
        assert breaker.failure_count == 2

        # Record error metric
        MetricsCollector.record_error("API_ERROR", "/test")
        MetricsCollector.update_circuit_breaker_state("api_test", 1, 2)

        # Metrics should be available
        metrics = get_metrics()
        assert isinstance(metrics, bytes)


class TestMetricsCollectorConcurrency:
    """Test metrics under concurrent operations."""

    def test_multiple_metrics_recorded(self):
        """Test multiple metrics can be recorded concurrently."""
        # Record various metrics
        for i in range(10):
            MetricsCollector.record_request(
                method="GET",
                endpoint=f"/endpoint-{i}",
                status=200,
                latency_sec=0.1 * i,
            )
            MetricsCollector.record_error(f"ERROR_{i}", f"/endpoint-{i}")

        # Get metrics
        metrics = get_metrics()
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0


class TestCircuitBreakerIntegration:
    """Test circuit breaker state machine."""

    def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker transitions between states."""
        breaker = circuit_breaker_registry.get_or_create("state_test")

        # Start in CLOSED
        assert breaker.state.value == "closed"

        # Record failures
        for _ in range(5):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass

        # Should be OPEN
        assert breaker.state.value == "open"

        # Circuit should reject calls
        with pytest.raises(CircuitBreakerException):
            breaker.call(lambda: "success")
