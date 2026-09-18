"""Bounded historical scans that never mutate incremental discovery state."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from github_stars_contrib_mcp.domain.audit import (
    AuditObservation,
    AuditRequest,
    AuditScanReport,
    AuditSourceScan,
    AuditSourceStatus,
)
from github_stars_contrib_mcp.domain.discovery import Evidence, SourceRecord
from github_stars_contrib_mcp.domain.ports.discovery_repository import SourceRepository
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterErrorKind,
    CapabilityStatus,
    SourceAdapter,
    SourceAdapterError,
    SourceBatch,
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class HistoricalAuditScanner:
    """Scan trusted sources with ephemeral adapter cursors only."""

    def __init__(
        self,
        repository: SourceRepository,
        adapters: Sequence[SourceAdapter] = (),
    ) -> None:
        self._repository = repository
        self._adapters = tuple(adapters)

    def _resolve_adapter(self, source: SourceRecord) -> SourceAdapter:
        matches = [adapter for adapter in self._adapters if adapter.supports(source)]
        if not matches:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                f"no adapter registered for source type {source.source_type.value}",
            )
        if len(matches) > 1:
            names = ", ".join(sorted(adapter.name for adapter in matches))
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                f"multiple adapters match source {source.id}: {names}",
            )
        return matches[0]

    @staticmethod
    def _validate_batch(source: SourceRecord, batch: SourceBatch) -> None:
        for emission in batch.emissions:
            if emission.item.source_id != source.id:
                raise SourceAdapterError(
                    AdapterErrorKind.PARSE,
                    "adapter emitted an item for a different source",
                )
            if any(evidence.source_id != source.id for evidence in emission.evidence):
                raise SourceAdapterError(
                    AdapterErrorKind.PARSE,
                    "adapter emitted evidence for a different source",
                )

    @staticmethod
    def _matches_request(request: AuditRequest, published_at: datetime | None) -> bool:
        if published_at is None:
            return False
        observed = _as_utc(published_at)
        return request.start <= observed <= request.end

    async def scan(self, request: AuditRequest) -> AuditScanReport:
        enabled = self._repository.list_sources(enabled_only=True)
        if request.source_ids:
            allowed_ids = set(request.source_ids)
            enabled = [source for source in enabled if source.id in allowed_ids]
        if request.source_types:
            allowed_types = set(request.source_types)
            enabled = [
                source for source in enabled if source.source_type in allowed_types
            ]
        enabled = sorted(enabled, key=lambda source: source.id)

        source_results: list[AuditSourceScan] = []
        observations: list[AuditObservation] = []

        for source in enabled:
            summary, source_observations = await self._scan_source(source, request)
            source_results.append(summary)
            observations.extend(source_observations)

        return AuditScanReport(
            request=request,
            sources=tuple(source_results),
            observations=tuple(observations),
        )

    async def _scan_source(
        self,
        source: SourceRecord,
        request: AuditRequest,
    ) -> tuple[AuditSourceScan, list[AuditObservation]]:
        summary = AuditSourceScan(
            source_id=source.id,
            source_type=source.source_type,
            status=AuditSourceStatus.UNAVAILABLE,
        )
        observations: list[AuditObservation] = []

        try:
            adapter = self._resolve_adapter(source)
            summary.adapter = adapter.name
            capability = adapter.capabilities(source)
            summary.capability = capability.status.value
            summary.reason = capability.reason
            if capability.status is CapabilityStatus.UNAVAILABLE:
                summary.status = AuditSourceStatus.UNAVAILABLE
                return summary, observations

            summary.status = (
                AuditSourceStatus.LIMITED
                if capability.status is CapabilityStatus.LIMITED
                else AuditSourceStatus.SEARCHED
            )

            # Deliberately start from an ephemeral cursor. Historical audit must never
            # read or mutate the repository's incremental discovery cursor.
            ephemeral_cursor = None
            async for batch in adapter.iter_items(source, ephemeral_cursor):
                if summary.batches_scanned >= request.max_batches_per_source:
                    summary.truncated = True
                    summary.status = AuditSourceStatus.TRUNCATED
                    break

                summary.batches_scanned += 1
                self._validate_batch(source, batch)
                ephemeral_cursor = batch.next_cursor

                for emission in batch.emissions:
                    if summary.items_seen >= request.max_items_per_source:
                        summary.truncated = True
                        summary.status = AuditSourceStatus.TRUNCATED
                        break

                    summary.items_seen += 1
                    item = emission.item
                    if item.published_at is None:
                        summary.undated_items += 1
                        continue
                    if not self._matches_request(request, item.published_at):
                        continue
                    if (
                        request.contribution_types
                        and item.type_hint not in set(request.contribution_types)
                    ):
                        continue

                    summary.items_in_window += 1
                    observations.append(
                        AuditObservation(
                            source_id=source.id,
                            adapter=adapter.name,
                            batch_index=summary.batches_scanned,
                            item=item,
                            evidence=tuple(
                                Evidence.model_validate(value)
                                for value in emission.evidence
                            ),
                        )
                    )

                if summary.truncated:
                    break

            return summary, observations
        except SourceAdapterError as exc:
            summary.status = (
                AuditSourceStatus.UNAVAILABLE
                if exc.kind is AdapterErrorKind.UNAVAILABLE
                else AuditSourceStatus.FAILED
            )
            summary.error_kind = exc.kind.value
            summary.reason = str(exc)
            return summary, observations
        except Exception as exc:
            summary.status = AuditSourceStatus.FAILED
            summary.error_kind = AdapterErrorKind.UNKNOWN.value
            summary.reason = str(exc)
            return summary, observations
