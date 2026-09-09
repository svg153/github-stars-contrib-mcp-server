"""Privacy-safe observability for autonomous contribution discovery."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import structlog
from prometheus_client import Counter, Histogram

from github_stars_contrib_mcp.observability.metrics import DEFAULT_REGISTRY

_DISCOVERY_RUNS = Counter(
    "mcp_discovery_runs_total",
    "Discovery runs grouped by terminal status",
    ["status"],
    registry=DEFAULT_REGISTRY,
)
_DISCOVERY_RUN_DURATION = Histogram(
    "mcp_discovery_run_duration_seconds",
    "Discovery run duration in seconds",
    ["status"],
    registry=DEFAULT_REGISTRY,
)
_DISCOVERY_SOURCES = Counter(
    "mcp_discovery_sources_total",
    "Discovery source executions grouped by bounded capability/status dimensions",
    ["source_type", "capability", "status", "error_class"],
    registry=DEFAULT_REGISTRY,
)
_DISCOVERY_SOURCE_DURATION = Histogram(
    "mcp_discovery_source_duration_seconds",
    "Discovery source duration in seconds",
    ["source_type", "capability", "status"],
    registry=DEFAULT_REGISTRY,
)
_DISCOVERY_CANDIDATES = Counter(
    "mcp_discovery_candidates_total",
    "Discovery candidates grouped by source type and duplicate class",
    ["source_type", "duplicate_class"],
    registry=DEFAULT_REGISTRY,
)

logger = structlog.get_logger(__name__)


class StructuredLogger(Protocol):
    def info(self, event: str, **kwargs: Any) -> Any: ...


def _bounded(value: str | None, *, fallback: str = "unknown") -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return fallback
    return normalized[:64]


class DiscoveryTelemetry:
    """Emit allowlisted discovery logs and low-cardinality Prometheus metrics."""

    def __init__(self, structured_logger: StructuredLogger | None = None) -> None:
        self._logger = structured_logger or logger

    @staticmethod
    def _emit_fields(
        *,
        run_id: str,
        source_type: str | None = None,
        capability: str | None = None,
        source_count: int | None = None,
        item_count: int = 0,
        candidate_count: int = 0,
        duplicate_class: str | None = None,
        duration_ms: float | None = None,
        error_class: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Return the complete allowlist for one structured event.

        Deliberately absent: source URLs/IDs, contribution URLs, titles, descriptions,
        evidence/page bodies, prompts, exception messages, credentials and tokens.
        """

        fields: dict[str, Any] = {"run_id": run_id}
        optional: Mapping[str, Any] = {
            "source_type": source_type,
            "capability": capability,
            "source_count": source_count,
            "item_count": item_count,
            "candidate_count": candidate_count,
            "duplicate_class": duplicate_class,
            "duration_ms": duration_ms,
            "error_class": error_class,
            "status": status,
        }
        for key, value in optional.items():
            if value is not None:
                fields[key] = value
        return fields

    def record_run(
        self,
        *,
        run_id: str,
        status: str,
        source_count: int,
        candidate_count: int,
        duration_s: float,
        error_class: str | None = None,
    ) -> None:
        status_label = _bounded(status)
        _DISCOVERY_RUNS.labels(status=status_label).inc()
        _DISCOVERY_RUN_DURATION.labels(status=status_label).observe(
            max(0.0, duration_s)
        )
        self._logger.info(
            "discovery_run",
            **self._emit_fields(
                run_id=run_id,
                source_count=max(0, source_count),
                item_count=max(0, candidate_count),
                candidate_count=max(0, candidate_count),
                duration_ms=round(max(0.0, duration_s) * 1000, 3),
                error_class=_bounded(error_class, fallback="none"),
                status=status_label,
            ),
        )

    def record_source(
        self,
        *,
        run_id: str,
        source_type: str,
        capability: str | None,
        status: str,
        item_count: int,
        candidate_count: int,
        duration_s: float,
        error_class: str | None = None,
    ) -> None:
        source_label = _bounded(source_type)
        capability_label = _bounded(capability)
        status_label = _bounded(status)
        error_label = _bounded(error_class, fallback="none")
        _DISCOVERY_SOURCES.labels(
            source_type=source_label,
            capability=capability_label,
            status=status_label,
            error_class=error_label,
        ).inc()
        _DISCOVERY_SOURCE_DURATION.labels(
            source_type=source_label,
            capability=capability_label,
            status=status_label,
        ).observe(max(0.0, duration_s))
        self._logger.info(
            "discovery_source",
            **self._emit_fields(
                run_id=run_id,
                source_type=source_label,
                capability=capability_label,
                item_count=max(0, item_count),
                candidate_count=max(0, candidate_count),
                duration_ms=round(max(0.0, duration_s) * 1000, 3),
                error_class=error_label,
                status=status_label,
            ),
        )

    def record_candidate_batch(
        self,
        *,
        run_id: str,
        source_type: str,
        capability: str | None,
        duplicate_class: str,
        item_count: int,
        candidate_count: int,
    ) -> None:
        source_label = _bounded(source_type)
        duplicate_label = _bounded(duplicate_class)
        _DISCOVERY_CANDIDATES.labels(
            source_type=source_label,
            duplicate_class=duplicate_label,
        ).inc(max(0, candidate_count))
        self._logger.info(
            "discovery_candidates",
            **self._emit_fields(
                run_id=run_id,
                source_type=source_label,
                capability=_bounded(capability),
                item_count=max(0, item_count),
                candidate_count=max(0, candidate_count),
                duplicate_class=duplicate_label,
            ),
        )
