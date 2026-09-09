"""Provider-neutral discovery run orchestration."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from time import monotonic
from typing import Protocol
from uuid import uuid4

from github_stars_contrib_mcp.application.discovery.confidence import assess_confidence
from github_stars_contrib_mcp.application.discovery.deduplicator import (
    Deduplicator,
    load_stars_snapshot,
)
from github_stars_contrib_mcp.application.discovery.normalizer import (
    normalize_candidate,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    DiscoveryRunStatus,
    DuplicateState,
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
from github_stars_contrib_mcp.domain.ports.stars_api import StarsAPIPort
from github_stars_contrib_mcp.observability.discovery import DiscoveryTelemetry


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
        stars_api: StarsAPIPort | None = None,
        telemetry: DiscoveryTelemetry | None = None,
    ) -> None:
        self._repository = repository
        self._adapters = tuple(adapters)
        self._stars_api = stars_api
        self._telemetry = telemetry or DiscoveryTelemetry()

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
    def _apply_assessment(
        source: SourceRecord,
        candidate: CandidateContribution,
        evidence: tuple | list,
        deduplicator: Deduplicator,
        local_candidates: list[CandidateContribution],
    ) -> CandidateContribution:
        if candidate.state is not CandidateState.DISCOVERED:
            return candidate

        match, fingerprints = deduplicator.assess(candidate, local_candidates)
        confidence = assess_confidence(
            source,
            candidate,
            evidence,
            duplicate_state=match.state,
        )
        candidate.duplicate_state = match.state
        candidate.ownership_confidence = confidence.ownership
        candidate.contribution_confidence = confidence.contribution
        metadata = candidate.provenance.metadata
        metadata["fingerprints"] = {
            "source": fingerprints.source,
            "url": fingerprints.url,
            "content": fingerprints.content,
            "canonical_url": fingerprints.canonical_url,
        }
        metadata["duplicate"] = {
            "state": match.state.value,
            "method": match.method,
            "reason": match.reason,
            "target": match.target,
        }
        metadata["confidence"] = {
            "ownership": {
                "score": confidence.ownership,
                "band": confidence.ownership_band,
                "reasons": list(confidence.ownership_reasons),
            },
            "contribution": {
                "score": confidence.contribution,
                "band": confidence.contribution_band,
                "reasons": list(confidence.contribution_reasons),
            },
        }

        if match.state is DuplicateState.EXACT:
            candidate.transition_to(CandidateState.BLOCKED_DUPLICATE)
        elif match.state in {DuplicateState.CLEAR, DuplicateState.LIKELY}:
            candidate.transition_to(CandidateState.REVIEW_READY)
        # UNKNOWN deliberately stays DISCOVERED: without Stars we cannot prove dedupe safety.
        return candidate

    async def run(
        self,
        *,
        source_ids: set[str] | None = None,
        dry_run: bool = False,
    ) -> DiscoveryRun:
        run_started = monotonic()
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

        snapshot = await load_stars_snapshot(self._stars_api)
        deduplicator = Deduplicator(snapshot)
        local_candidates = self._repository.list_candidates()
        run.summary["stars_dedupe"] = {
            "available": snapshot.available,
            "contributions_loaded": len(snapshot.contributions),
            "error": snapshot.error,
        }

        succeeded = 0
        for source in enabled:
            source_started = monotonic()
            capability_label = "unknown"
            error_kind: str | None = None
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
                capability_label = capability.status.value
                source_summary["capability"] = capability_label
                source_summary["capability_reason"] = capability.reason
                if capability.status is CapabilityStatus.UNAVAILABLE:
                    raise SourceAdapterError(
                        AdapterErrorKind.UNAVAILABLE,
                        capability.reason or "adapter capability unavailable",
                    )

                cursor = self._repository.get_cursor(source.id)
                async for batch in adapter.iter_items(source, cursor):
                    self._validate_batch(source, batch)
                    prepared = []
                    for emission in batch.emissions:
                        candidate = _preserve_reviewed_candidate(
                            self._repository,
                            normalize_candidate(
                                source,
                                emission.item,
                                adapter_name=adapter.name,
                                adapter_version=adapter.version,
                            ),
                        )
                        candidate = self._apply_assessment(
                            source,
                            candidate,
                            emission.evidence,
                            deduplicator,
                            local_candidates,
                        )
                        prepared.append((candidate, emission.evidence))
                        if not any(
                            item.id == candidate.id for item in local_candidates
                        ):
                            local_candidates.append(candidate)

                    if not dry_run:
                        with self._repository.transaction():
                            for candidate, evidence in prepared:
                                self._repository.save_candidate(candidate, evidence)
                            if batch.next_cursor is not None:
                                self._repository.save_cursor(
                                    source.id, batch.next_cursor
                                )

                    duplicate_counts = Counter(
                        candidate.duplicate_state.value
                        for candidate, _evidence in prepared
                    )
                    for duplicate_class, count in sorted(duplicate_counts.items()):
                        self._telemetry.record_candidate_batch(
                            run_id=run.id,
                            source_type=source.source_type.value,
                            capability=capability_label,
                            duplicate_class=duplicate_class,
                            item_count=count,
                            candidate_count=count,
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
                error_kind, message = _classify_error(exc)
                source_summary["status"] = "failed"
                source_summary["error_kind"] = error_kind
                run.errors.append(
                    {"source_id": source.id, "kind": error_kind, "message": message}
                )
            finally:
                self._telemetry.record_source(
                    run_id=run.id,
                    source_type=source.source_type.value,
                    capability=capability_label,
                    status=str(source_summary["status"]),
                    item_count=int(source_summary["candidates"]),
                    candidate_count=int(source_summary["candidates"]),
                    duration_s=monotonic() - source_started,
                    error_class=error_kind,
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
        self._telemetry.record_run(
            run_id=run.id,
            status=run.status.value,
            source_count=len(enabled),
            candidate_count=int(run.summary["candidates_seen"]),
            duration_s=monotonic() - run_started,
            error_class="source_failure" if failed else None,
        )
        return run
