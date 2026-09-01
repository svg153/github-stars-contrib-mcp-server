"""Optional OpenTelemetry tracing exported through standard OTLP/HTTP."""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class TracingConfig:
    service_name: str = "github-stars-contrib-mcp"
    endpoint: str = "http://localhost:4318/v1/traces"
    enabled: bool = False


class DistributedTracer:
    def __init__(self, config: TracingConfig):
        self.config = config
        self.tracer: trace.Tracer | None = None
        self.provider: TracerProvider | None = None
        if config.enabled:
            self._initialize_tracing()

    def _initialize_tracing(self) -> None:
        try:
            self.provider = TracerProvider(
                resource=Resource.create({SERVICE_NAME: self.config.service_name})
            )
            exporter = OTLPSpanExporter(endpoint=self.config.endpoint)
            self.provider.add_span_processor(BatchSpanProcessor(exporter))
            self.tracer = self.provider.get_tracer(__name__)
            logger.info(
                "tracing_initialized",
                service=self.config.service_name,
                otlp_endpoint=self.config.endpoint,
            )
        except Exception as exc:
            logger.error(
                "tracing_initialization_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            self.tracer = None
            self.provider = None

    @contextmanager
    def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> Generator[trace.Span | None, None, None]:
        if not self.config.enabled or self.tracer is None:
            yield None
            return
        with self.tracer.start_as_current_span(name) as span:
            for key, value in (attributes or {}).items():
                span.set_attribute(key, value)
            yield span

    def add_event(
        self,
        span: trace.Span | None,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        if span is not None:
            span.add_event(name, attributes or {})

    def shutdown(self) -> None:
        if self.provider is not None:
            self.provider.force_flush()
            self.provider.shutdown()


_tracer_instance: DistributedTracer | None = None


def get_tracer() -> DistributedTracer:
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = DistributedTracer(TracingConfig())
    return _tracer_instance


def initialize_tracing(config: TracingConfig) -> DistributedTracer:
    global _tracer_instance
    if _tracer_instance is not None:
        _tracer_instance.shutdown()
    _tracer_instance = DistributedTracer(config)
    return _tracer_instance


def shutdown_tracing() -> None:
    global _tracer_instance
    if _tracer_instance is not None:
        _tracer_instance.shutdown()
        _tracer_instance = None
