"""Provider-neutral discovery run orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import uuid4

from github_stars_contrib_mcp.application.discovery.normalizer import (
    normalize_candidate,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    DiscoveryRunStatus,
    SourceRecord,
    utc_now,
)
from github_stars_contrib_mcp.domain.ports.discovery_repository import (
    CandidateRepository,
    DiscoveryRunRepository,
    DiscoveryUnitOfWork,
    SourceRepository,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterErrorKind,
    CapabilityStatus,
    SourceAdapter,
    SourceAdapterError,
    SourceBatch,
)


class DiscoveryRepository(
    SourceRepository,
    CandidateRepository,
    DiscoveryRunRepository,
    DiscoveryUnitOfWork,
    Protocol,
):
    """Composite repository shape required by discovery orchestration."""


def _classify_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, SourceAdapterError):
        return exc.kind.value, str(exc)
    return AdapterErrorKind.UNKNOWN.value, str(exc)


def _preserve_reviewed_candidate(
    repository: CandidateRepository,
    candidate: CandidateContribution,
) -> CandidateContribution:
    """Never let rediscovery undo a human/lifecycle decision."""

    existing = repository.get_candidate(candidate.id)
    if existing is None:
        return candidate
    if existing.state is not CandidateState.DISCOVERED:
        return existing
    candidate.created_at = existing.created_at
    return candidate


class DiscoveryOrchestrator:
    """Run enabled sources independently and checkpoint batches atomically."""

    def __init__(
        self,
        repository: DiscoveryRepository,
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

    async def run(
        self,
        *,
        source_ids: set[str] | None = None,
        dry_run: bool = False,
    ) -> DiscoveryRun:
        enabled = self._repository.list_sources(enabled_only=True)
        if source_ids is not None:
            enabled = [source for source in enabled if source.id in source_ids]
        enabled = sorted(enabled, key=lambda source: source.id)

        run = DiscoveryRun(
            id=f"discovery:{uuid4().hex}",
            source_ids=[source.id for source in enabled],
            summary={
                "dry_run": dry_run,
                "sources_total": len(enabled),
                "sources_succeeded": 0,
                "sources_failed": 0,
                "candidates_seen": 0,
                "batches_seen": 0,
                "sources": {},
            },
        )
        self._repository.save_run(run)

        succeeded = 0
        for source in enabled:
            source_summary: dict[str, object] = {
                "status": "running",
                "adapter": None,
                "capability": None,
                "capability_reason": None,
                "batches": 0,
                "candidates": 0,
            }
            run.summary["sources"][source.id] = source_summary
            try:
                adapter = self._resolve_adapter(source)
                source_summary["adapter"] = adapter.name
                capability = adapter.capabilities(source)
                source_summary["capability"] = capability.status.value
                source_summary["capability_reason"] = capability.reason
                if capability.status is CapabilityStatus.UNAVAILABLE:
                    raise SourceAdapterError(
                        AdapterErrorKind.UNAVAILABLE,
                        capability.reason or "adapter capability unavailable",
                    )

                cursor = self._repository.get_cursor(source.id)
                async for batch in adapter.iter_items(source, cursor):
                    self._validate_batch(source, batch)
                    prepared = [
                        (
                            _preserve_reviewed_candidate(
                                self._repository,
                                normalize_candidate(
                                    source,
                                    emission.item,
                                    adapter_name=adapter.name,
                                    adapter_version=adapter.version,
                                ),
                            ),
                            emission.evidence,
                        )
                        for emission in batch.emissions
                    ]
                    if not dry_run:
                        with self._repository.transaction():
                            for candidate, evidence in prepared:
                                self._repository.save_candidate(candidate, evidence)
                            if batch.next_cursor is not None:
                                self._repository.save_cursor(
                                    source.id,
                                    batch.next_cursor,
                                )

                    source_summary["batches"] = int(source_summary["batches"]) + 1
                    source_summary["candidates"] = int(
                        source_summary["candidates"]
                    ) + len(prepared)
                    run.summary["batches_seen"] += 1
                    run.summary["candidates_seen"] += len(prepared)

                source_summary["status"] = "completed"
                succeeded += 1
            except Exception as exc:
                kind, message = _classify_error(exc)
                source_summary["status"] = "failed"
                source_summary["error_kind"] = kind
                run.errors.append(
                    {
                        "source_id": source.id,
                        "kind": kind,
                        "message": message,
                    }
                )

        failed = len(enabled) - succeeded
        run.summary["sources_succeeded"] = succeeded
        run.summary["sources_failed"] = failed
        if failed == 0:
            run.status = DiscoveryRunStatus.COMPLETED
        elif succeeded > 0:
            run.status = DiscoveryRunStatus.PARTIAL
        else:
            run.status = DiscoveryRunStatus.FAILED
        run.finished_at = utc_now()
        self._repository.save_run(run)
        return run
