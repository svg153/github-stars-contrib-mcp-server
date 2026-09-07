"""Deterministic, explainable confidence scoring for discovery candidates."""

from __future__ import annotations

from dataclasses import dataclass

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    DuplicateState,
    Evidence,
    OwnershipStatus,
    SourceRecord,
)


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    ownership: float
    contribution: float
    ownership_band: str
    contribution_band: str
    ownership_reasons: tuple[str, ...]
    contribution_reasons: tuple[str, ...]


def _band(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def assess_confidence(
    source: SourceRecord,
    candidate: CandidateContribution,
    evidence: tuple[Evidence, ...] | list[Evidence] = (),
    *,
    duplicate_state: DuplicateState,
) -> ConfidenceAssessment:
    ownership_weights = {
        OwnershipStatus.VERIFIED: 0.95,
        OwnershipStatus.EXPLICIT: 0.85,
        OwnershipStatus.INFERRED: 0.5,
        OwnershipStatus.REJECTED: 0.0,
    }
    ownership = ownership_weights[source.ownership]
    ownership_reasons = [f"source_ownership:{source.ownership.value}"]
    if source.evidence:
        ownership = min(1.0, ownership + 0.05)
        ownership_reasons.append("source_has_ownership_evidence")

    contribution = 0.25
    contribution_reasons = ["candidate_discovered"]
    if candidate.external_id.strip():
        contribution += 0.15
        contribution_reasons.append("provider_external_id")
    if candidate.title.strip():
        contribution += 0.15
        contribution_reasons.append("structured_title")
    if candidate.date is not None:
        contribution += 0.15
        contribution_reasons.append("structured_date")
    if candidate.contribution_type is not None:
        contribution += 0.15
        contribution_reasons.append("structured_type")
    if evidence:
        contribution += min(0.1, 0.05 * len(evidence))
        contribution_reasons.append(f"evidence_count:{len(evidence)}")

    metadata = candidate.provenance.metadata
    if metadata.get("speaker_identity_verified") or metadata.get(
        "author_identity_verified"
    ):
        contribution += 0.05
        contribution_reasons.append("author_or_speaker_identity")
    if duplicate_state is DuplicateState.LIKELY:
        contribution -= 0.15
        contribution_reasons.append("ambiguity_penalty:likely_duplicate")
    elif duplicate_state is DuplicateState.UNKNOWN:
        contribution -= 0.1
        contribution_reasons.append("ambiguity_penalty:duplicate_unknown")

    contribution = max(0.0, min(1.0, contribution))
    return ConfidenceAssessment(
        ownership=ownership,
        contribution=contribution,
        ownership_band=_band(ownership),
        contribution_band=_band(contribution),
        ownership_reasons=tuple(ownership_reasons),
        contribution_reasons=tuple(contribution_reasons),
    )
