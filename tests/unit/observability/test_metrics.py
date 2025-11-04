"""Tests for metrics and observability."""

from github_stars_contrib_mcp.observability import (
    MetricsCollector,
    get_metrics,
)


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_record_request(self):
        """Test recording request metrics."""
        MetricsCollector.record_request(
            method="GET",
            endpoint="/contributions",
            status=200,
            latency_sec=0.5,
            req_size=100,
            resp_size=1000,
        )
        # Should not raise

    def test_record_error(self):
        """Test recording error metrics."""
        MetricsCollector.record_error(
            error_type="HTTP_ERROR",
            endpoint="/contributions",
        )
        # Should not raise

    def test_record_contribution_created(self):
        """Test recording contribution creation."""
        MetricsCollector.record_contribution_created("LINK")
        MetricsCollector.record_contribution_created("PULL_REQUEST")
        # Should not raise

    def test_record_contribution_updated(self):
        """Test recording contribution update."""
        MetricsCollector.record_contribution_updated("LINK")
        # Should not raise

    def test_record_contribution_deleted(self):
        """Test recording contribution deletion."""
        MetricsCollector.record_contribution_deleted()
        # Should not raise

    def test_cache_metrics(self):
        """Test cache metrics recording."""
        MetricsCollector.record_cache_hit("url_validation")
        MetricsCollector.record_cache_miss("url_validation")
        MetricsCollector.set_cache_size("url_validation", 5120)
        # Should not raise

    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics."""
        MetricsCollector.update_circuit_breaker_state(
            name="stars_api",
            state=0,  # CLOSED
            failures=0,
        )
        # Should not raise

    def test_get_metrics_returns_bytes(self):
        """Test get_metrics returns Prometheus format."""
        metrics = get_metrics()
        assert isinstance(metrics, bytes)
        assert b"mcp_requests_total" in metrics or b"# HELP" in metrics
