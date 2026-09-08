"""Auditable human review workflows for discovered contribution candidates."""

from __future__ import annotations

from typing import Any, Protocol

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DuplicateState,
    ReviewDecision,
    ReviewDecisionType,
)
from github_stars_contrib_mcp.domain.ports.discovery_repository import (
    CandidateRepository,
    DiscoveryUnitOfWork,
    SourceRepository,
)
from github_stars_contrib_mcp.models import ContributionUpsertInput


class ReviewRepository(
    CandidateRepository,
    SourceRepository,
    DiscoveryUnitOfWork,
    Protocol,
):
    """Composite repository required by candidate review."""


_EDITABLE_FIELDS = frozenset(
    {"title", "url", "description", "contribution_type", "date"}
)


def _dump(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class ReviewCandidates:
    """Inspect and apply explicit, persisted human review decisions."""

    def __init__(self, repository: ReviewRepository) -> None:
        self._repository = repository

    def list(
        self,
        *,
        states: set[CandidateState] | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self._detail(candidate)
            for candidate in self._repository.list_candidates(states=states)
        ]

    def get(self, candidate_id: str) -> dict[str, Any]:
        return self._detail(self._require(candidate_id))

    def review(
        self,
        candidate_id: str,
        decision: ReviewDecisionType | str,
        *,
        reason: str | None = None,
        edits: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        candidate = self._require(candidate_id).model_copy(deep=True)
        resolved_decision = ReviewDecisionType(decision)
        changed = self._apply_edits(candidate, edits or {})

        if candidate.state in {CandidateState.REJECTED, CandidateState.PUBLISHED}:
            raise ValueError(f"candidate state {candidate.state.value} is terminal")

        if resolved_decision is ReviewDecisionType.APPROVE:
            if candidate.duplicate_state is DuplicateState.EXACT:
                raise ValueError("exact duplicate candidates cannot be approved")
            self._validate_publishable(candidate)
            if candidate.state is CandidateState.APPROVED and changed:
                candidate.transition_to(CandidateState.REVIEW_READY)
            self._ensure_review_ready(candidate)
            candidate.transition_to(CandidateState.APPROVED)
        elif resolved_decision is ReviewDecisionType.REJECT:
            if candidate.state is CandidateState.APPROVED:
                candidate.transition_to(CandidateState.REVIEW_READY)
            self._ensure_review_ready(candidate)
            candidate.transition_to(CandidateState.REJECTED)
        else:
            if candidate.state is CandidateState.APPROVED:
                candidate.transition_to(CandidateState.REVIEW_READY)
            self._ensure_review_ready(candidate)
            candidate.transition_to(CandidateState.DEFERRED)

        audit = ReviewDecision(
            candidate_id=candidate.id,
            decision=resolved_decision,
            reason=(
                reason.strip() if isinstance(reason, str) and reason.strip() else None
            ),
            edited_fields=changed,
        )
        with self._repository.transaction():
            self._repository.save_candidate(candidate)
            self._repository.record_review(audit)
        return self._detail(candidate)

    def _detail(self, candidate: CandidateContribution) -> dict[str, Any]:
        source = self._repository.get_source(candidate.source_id)
        evidence = self._repository.list_evidence(candidate.id)
        return {
            "candidate": candidate.model_dump(mode="json"),
            "source": source.model_dump(mode="json") if source is not None else None,
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }

    def _require(self, candidate_id: str) -> CandidateContribution:
        candidate = self._repository.get_candidate(candidate_id)
        if candidate is None:
            raise KeyError(f"Unknown candidate: {candidate_id}")
        return candidate

    @staticmethod
    def _apply_edits(
        candidate: CandidateContribution,
        edits: dict[str, Any],
    ) -> dict[str, Any]:
        unknown = set(edits) - _EDITABLE_FIELDS
        if unknown:
            raise ValueError(
                "unsupported candidate edit fields: " + ", ".join(sorted(unknown))
            )
        if not edits:
            return {}

        payload = candidate.model_dump()
        changed_keys = {
            key for key, value in edits.items() if payload.get(key) != value
        }
        if not changed_keys:
            return {}
        payload.update(edits)
        updated = CandidateContribution.model_validate(payload)
        for key in _EDITABLE_FIELDS:
            setattr(candidate, key, getattr(updated, key))
        return {key: _dump(getattr(candidate, key)) for key in sorted(changed_keys)}

    @staticmethod
    def _ensure_review_ready(candidate: CandidateContribution) -> None:
        if candidate.state in {
            CandidateState.BLOCKED_DUPLICATE,
            CandidateState.DISCOVERED,
        }:
            candidate.transition_to(CandidateState.REVIEW_READY)

    @staticmethod
    def _validate_publishable(candidate: CandidateContribution) -> None:
        if candidate.contribution_type is None or candidate.date is None:
            raise ValueError("approval requires contribution_type and date")
        ContributionUpsertInput(
            title=candidate.title,
            url=candidate.url,
            description=candidate.description,
            type=candidate.contribution_type,
            date=candidate.date,
        )
