"""
Distributed tracing with OpenTelemetry.
Provides end-to-end request tracing across services.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)


class TracingConfig:
    """Configuration for distributed tracing."""

    def __init__(
        self,
        service_name: str = "github-stars-contrib-mcp",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        enabled: bool = False,
    ):
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.enabled = enabled

    def __repr__(self) -> str:
        return f"TracingConfig({self.service_name}@{self.jaeger_host}:{self.jaeger_port}, enabled={self.enabled})"


class DistributedTracer:
    """
    Distributed tracing manager.

    Integrates with Jaeger/OpenTelemetry for end-to-end request tracing.
    """

    def __init__(self, config: TracingConfig):
        self.config = config
        self.tracer: trace.Tracer | None = None

        if config.enabled:
            self._initialize_tracing()

    def _initialize_tracing(self) -> None:
        """Initialize OpenTelemetry with Jaeger exporter."""
        try:
            # Create Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_host,
                agent_port=self.config.jaeger_port,
            )

            # Set up trace provider
            trace_provider = TracerProvider(
                resource=Resource.create({SERVICE_NAME: self.config.service_name})
            )
            trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            trace.set_tracer_provider(trace_provider)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            # Instrument httpx automatically
            HTTPXClientInstrumentor().instrument()

            logger.info(
                "tracing_initialized",
                service=self.config.service_name,
                jaeger_endpoint=f"{self.config.jaeger_host}:{self.config.jaeger_port}",
            )
        except Exception as e:
            logger.error(
                "tracing_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            self.tracer = None

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[trace.Span | None, None, None]:
        """
        Create a named span for tracing.

        Usage:
            with tracer.span("operation_name", {"key": "value"}) as span:
                # do work
                pass
        """
        if not self.config.enabled or self.tracer is None:
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> trace.Span | None:
        """Start a span without context manager."""
        if not self.config.enabled or self.tracer is None:
            return None

        span = self.tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span

    def end_span(self, span: trace.Span | None) -> None:
        """End a span."""
        if span is not None:
            span.end()

    def add_event(
        self,
        span: trace.Span | None,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Add an event to a span."""
        if span is not None:
            span.add_event(name, attributes or {})

    def shutdown(self) -> None:
        """Shutdown tracing gracefully."""
        if self.tracer is None:
            return

        try:
            # Get the tracer provider and shutdown
            provider = trace.get_tracer_provider()
            if hasattr(provider, "force_flush"):
                provider.force_flush()  # type: ignore[attr-defined]
            logger.info("tracing_shutdown", service=self.config.service_name)
        except Exception as e:
            logger.error("tracing_shutdown_failed", error=str(e))


# Global tracing instance (initialize in server startup)
_tracer_instance: DistributedTracer | None = None


def get_tracer() -> DistributedTracer:
    """Get global tracer instance."""
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = DistributedTracer(TracingConfig(enabled=False))
    return _tracer_instance


def initialize_tracing(config: TracingConfig) -> DistributedTracer:
    """Initialize and set global tracer."""
    global _tracer_instance
    _tracer_instance = DistributedTracer(config)
    return _tracer_instance


def shutdown_tracing() -> None:
    """Shutdown global tracer."""
    global _tracer_instance
    if _tracer_instance is not None:
        _tracer_instance.shutdown()
        _tracer_instance = None
