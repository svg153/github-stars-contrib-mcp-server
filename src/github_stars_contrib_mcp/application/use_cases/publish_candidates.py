"""Guarded publication of explicitly approved discovery candidates."""

from __future__ import annotations

import hashlib
from typing import Any, Protocol

from pydantic import BaseModel

from github_stars_contrib_mcp.application.discovery.deduplicator import (
    Deduplicator,
    DuplicateMatch,
    load_stars_snapshot,
)
from github_stars_contrib_mcp.application.use_cases.upsert_contribution import (
    UpsertContribution,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DuplicateState,
)
from github_stars_contrib_mcp.domain.ports.discovery_repository import (
    CandidateRepository,
    DiscoveryUnitOfWork,
)
from github_stars_contrib_mcp.domain.ports.stars_api import StarsAPIPort
from github_stars_contrib_mcp.models import ContributionUpsertInput
from github_stars_contrib_mcp.utils.normalization import normalize_description


class PublishRepository(CandidateRepository, DiscoveryUnitOfWork, Protocol):
    """Composite repository required by publication."""


class PublishCandidateResult(BaseModel):
    candidate_id: str
    status: str
    client_id: str | None = None
    payload: dict[str, Any] | None = None
    duplicate_state: DuplicateState | None = None
    reason: str | None = None
    result: dict[str, Any] | None = None


def stable_client_id(candidate_id: str) -> str:
    digest = hashlib.sha256(candidate_id.encode()).hexdigest()[:32]
    return f"discovery-{digest}"


def _payload(candidate: CandidateContribution) -> dict[str, Any]:
    if candidate.contribution_type is None or candidate.date is None:
        raise ValueError("publication requires contribution_type and date")
    validated = ContributionUpsertInput(
        title=candidate.title,
        url=candidate.url,
        description=candidate.description,
        type=candidate.contribution_type,
        date=candidate.date,
    )
    return {
        "title": validated.title,
        "url": str(validated.url),
        "description": normalize_description(validated.description),
        "type": validated.type.value,
        "date": validated.date.isoformat(),
    }


class PublishCandidates:
    """Publish only previously approved candidates after a fresh policy check."""

    def __init__(
        self,
        repository: PublishRepository,
        stars_api: StarsAPIPort,
    ) -> None:
        self._repository = repository
        self._stars_api = stars_api
        self._upsert = UpsertContribution(stars_api)

    async def __call__(
        self,
        candidate_ids: list[str],
        *,
        dry_run: bool = True,
    ) -> list[PublishCandidateResult]:
        seen: set[str] = set()
        results: list[PublishCandidateResult] = []
        for candidate_id in candidate_ids:
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            results.append(await self._publish_one(candidate_id, dry_run=dry_run))
        return results

    async def _publish_one(
        self,
        candidate_id: str,
        *,
        dry_run: bool,
    ) -> PublishCandidateResult:
        candidate = self._repository.get_candidate(candidate_id)
        if candidate is None:
            return PublishCandidateResult(
                candidate_id=candidate_id,
                status="not_found",
                reason="unknown candidate",
            )

        client_id = stable_client_id(candidate.id)
        if candidate.state is CandidateState.PUBLISHED:
            return PublishCandidateResult(
                candidate_id=candidate.id,
                status="already_published",
                client_id=client_id,
            )
        if candidate.state is not CandidateState.APPROVED:
            return PublishCandidateResult(
                candidate_id=candidate.id,
                status="not_approved",
                client_id=client_id,
                duplicate_state=candidate.duplicate_state,
                reason="explicit persisted approval is required before publication",
            )

        try:
            payload = _payload(candidate)
        except Exception as exc:
            return PublishCandidateResult(
                candidate_id=candidate.id,
                status="invalid",
                client_id=client_id,
                reason=str(exc),
            )

        snapshot = await load_stars_snapshot(self._stars_api)
        if not snapshot.available:
            return PublishCandidateResult(
                candidate_id=candidate.id,
                status="blocked",
                client_id=client_id,
                payload=payload,
                duplicate_state=DuplicateState.UNKNOWN,
                reason=snapshot.error or "fresh Stars duplicate check unavailable",
            )

        local = self._repository.list_candidates()
        match, fingerprints = Deduplicator(snapshot).assess(candidate, local)
        if match.state is not DuplicateState.CLEAR:
            if not dry_run:
                self._persist_block(candidate, match, fingerprints)
            return PublishCandidateResult(
                candidate_id=candidate.id,
                status="blocked",
                client_id=client_id,
                payload=payload,
                duplicate_state=match.state,
                reason=match.reason,
            )

        if dry_run:
            return PublishCandidateResult(
                candidate_id=candidate.id,
                status="dry_run",
                client_id=client_id,
                payload=payload,
                duplicate_state=DuplicateState.CLEAR,
                reason="fresh duplicate check passed; no Stars write performed",
            )

        result = await self._upsert(client_id, payload)
        evidence = self._repository.list_evidence(candidate.id)
        candidate.duplicate_state = DuplicateState.CLEAR
        candidate.provenance.metadata["final_publish_check"] = {
            "state": match.state.value,
            "method": match.method,
            "reason": match.reason,
            "target": match.target,
            "fingerprints": {
                "source": fingerprints.source,
                "url": fingerprints.url,
                "content": fingerprints.content,
                "canonical_url": fingerprints.canonical_url,
            },
        }
        candidate.transition_to(CandidateState.PUBLISHED)
        publication_record = {
            "api_result": result,
            "candidate": candidate.model_dump(mode="json"),
            "evidence_ids": [item.id for item in evidence],
            "provenance": candidate.provenance.model_dump(mode="json"),
            "duplicate_check": candidate.provenance.metadata["final_publish_check"],
        }
        with self._repository.transaction():
            self._repository.save_candidate(candidate)
            self._repository.record_publication(
                candidate.id,
                client_id,
                publication_record,
            )
        return PublishCandidateResult(
            candidate_id=candidate.id,
            status="published",
            client_id=client_id,
            payload=payload,
            duplicate_state=DuplicateState.CLEAR,
            result=result,
        )

    def _persist_block(
        self,
        candidate: CandidateContribution,
        match: DuplicateMatch,
        fingerprints: Any,
    ) -> None:
        blocked = candidate.model_copy(deep=True)
        blocked.duplicate_state = match.state
        blocked.provenance.metadata["final_publish_check"] = {
            "state": match.state.value,
            "method": match.method,
            "reason": match.reason,
            "target": match.target,
            "fingerprints": {
                "source": fingerprints.source,
                "url": fingerprints.url,
                "content": fingerprints.content,
                "canonical_url": fingerprints.canonical_url,
            },
        }
        if match.state is DuplicateState.EXACT:
            blocked.transition_to(CandidateState.BLOCKED_DUPLICATE)
        elif match.state is DuplicateState.LIKELY:
            blocked.transition_to(CandidateState.REVIEW_READY)
        with self._repository.transaction():
            self._repository.save_candidate(blocked)
