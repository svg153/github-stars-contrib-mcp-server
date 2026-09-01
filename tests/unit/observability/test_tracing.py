"""Tests for optional OTLP tracing."""

from github_stars_contrib_mcp.observability.tracing import (
    DistributedTracer,
    TracingConfig,
)


def test_disabled_tracer_is_noop():
    tracer = DistributedTracer(TracingConfig(enabled=False))
    with tracer.span("unit") as span:
        assert span is None


def test_tracing_config_defaults_to_standard_otlp_http():
    config = TracingConfig()
    assert config.service_name == "github-stars-contrib-mcp"
    assert config.endpoint.endswith("/v1/traces")
    assert config.enabled is False
