"""Tests for distributed tracing."""

from github_stars_contrib_mcp.observability import (
    DistributedTracer,
    TracingConfig,
    get_tracer,
    initialize_tracing,
    shutdown_tracing,
)


class TestTracingConfig:
    """Tests for TracingConfig."""

    def test_config_creation(self):
        """Test creating tracing config."""
        config = TracingConfig(
            service_name="test-service",
            jaeger_host="jaeger-local",
            jaeger_port=6831,
            enabled=False,
        )

        assert config.service_name == "test-service"
        assert config.jaeger_host == "jaeger-local"
        assert config.jaeger_port == 6831
        assert config.enabled is False

    def test_config_repr(self):
        """Test config string representation."""
        config = TracingConfig(enabled=False)
        repr_str = repr(config)
        assert "github-stars-contrib-mcp" in repr_str
        assert "localhost" in repr_str


class TestDistributedTracer:
    """Tests for DistributedTracer."""

    def test_tracer_disabled(self):
        """Test tracer with disabled config."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        assert tracer.tracer is None
        assert tracer.config.enabled is False

    def test_span_when_disabled(self):
        """Test span context manager when tracing disabled."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        with tracer.span("test_span", {"key": "value"}) as span:
            assert span is None

    def test_start_span_when_disabled(self):
        """Test start_span when tracing disabled."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        span = tracer.start_span("test", {"attr": "value"})
        assert span is None

    def test_end_span(self):
        """Test end_span with None."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        tracer.end_span(None)  # Should not raise

    def test_add_event(self):
        """Test add_event with None span."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        tracer.add_event(None, "test_event", {"key": "value"})  # Should not raise

    def test_shutdown(self):
        """Test shutdown."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        tracer.shutdown()  # Should not raise


class TestGlobalTracerInstance:
    """Tests for global tracer instance."""

    def test_get_tracer_returns_instance(self):
        """Test get_tracer returns DistributedTracer."""
        tracer = get_tracer()
        assert isinstance(tracer, DistributedTracer)
        assert tracer.config.enabled is False

    def test_initialize_tracing(self):
        """Test initialize_tracing."""
        config = TracingConfig(service_name="test", enabled=False)
        tracer = initialize_tracing(config)

        assert isinstance(tracer, DistributedTracer)
        assert tracer.config.service_name == "test"

    def test_shutdown_tracing(self):
        """Test shutdown_tracing."""
        shutdown_tracing()  # Should not raise
