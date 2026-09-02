"""Deterministic provider-neutral source item normalization."""

from __future__ import annotations

import hashlib

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    OwnershipStatus,
    Provenance,
    SourceItem,
    SourceRecord,
)

NORMALIZER_VERSION = "1"

_OWNERSHIP_CONFIDENCE = {
    OwnershipStatus.VERIFIED: 1.0,
    OwnershipStatus.EXPLICIT: 0.9,
    OwnershipStatus.INFERRED: 0.5,
    OwnershipStatus.REJECTED: 0.0,
}


def _candidate_id(source_id: str, external_id: str) -> str:
    material = f"{source_id}\0{external_id}".encode()
    return f"candidate:{hashlib.sha256(material).hexdigest()}"


def normalize_candidate(
    source: SourceRecord,
    item: SourceItem,
    *,
    adapter_name: str,
    adapter_version: str,
) -> CandidateContribution:
    """Create a stable candidate without fabricating missing publication data."""

    if item.source_id != source.id:
        raise ValueError("source item does not belong to the source being normalized")

    review_reasons: list[str] = []
    if item.type_hint is None:
        review_reasons.append("missing_contribution_type")
    if item.published_at is None:
        review_reasons.append("missing_publication_date")

    if item.type_hint is not None and item.published_at is not None:
        contribution_confidence = 0.95
    elif item.type_hint is not None or item.published_at is not None:
        contribution_confidence = 0.7
    else:
        contribution_confidence = 0.5

    return CandidateContribution(
        id=_candidate_id(source.id, item.external_id),
        source_id=source.id,
        external_id=item.external_id,
        title=item.title,
        url=item.url,
        description=item.description,
        contribution_type=item.type_hint,
        date=item.published_at,
        state=CandidateState.DISCOVERED,
        ownership_confidence=_OWNERSHIP_CONFIDENCE[source.ownership],
        contribution_confidence=contribution_confidence,
        provenance=Provenance(
            adapter=adapter_name,
            adapter_version=adapter_version,
            normalizer_version=NORMALIZER_VERSION,
            metadata={
                "review_required": bool(review_reasons),
                "review_reasons": review_reasons,
                "structured_type_hint": item.type_hint is not None,
                "structured_publication_date": item.published_at is not None,
            },
        ),
    )
