"""Provider-neutral discovery domain models and lifecycle rules."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from github_stars_contrib_mcp.models import ContributionType

SCHEMA_VERSION = 1


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class DiscoveryTransitionError(ValueError):
    """Raised when a candidate lifecycle transition is not allowed."""


class SourceType(StrEnum):
    RSS = "rss"
    WEBSITE = "website"
    GITHUB = "github"
    YOUTUBE = "youtube"
    SESSIONIZE = "sessionize"
    PRETALX = "pretalx"
    X = "x"
    LINKEDIN = "linkedin"
    UNKNOWN = "unknown"


class OwnershipStatus(StrEnum):
    EXPLICIT = "explicit"
    VERIFIED = "verified"
    INFERRED = "inferred"
    REJECTED = "rejected"


class CandidateState(StrEnum):
    DISCOVERED = "discovered"
    REVIEW_READY = "review_ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    BLOCKED_DUPLICATE = "blocked_duplicate"
    PUBLISHED = "published"


class DuplicateState(StrEnum):
    UNKNOWN = "unknown"
    CLEAR = "clear"
    LIKELY = "likely"
    EXACT = "exact"


class ReviewDecisionType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


class DiscoveryRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


_ALLOWED_TRANSITIONS: dict[CandidateState, frozenset[CandidateState]] = {
    CandidateState.DISCOVERED: frozenset(
        {CandidateState.REVIEW_READY, CandidateState.BLOCKED_DUPLICATE}
    ),
    CandidateState.REVIEW_READY: frozenset(
        {
            CandidateState.APPROVED,
            CandidateState.REJECTED,
            CandidateState.DEFERRED,
            CandidateState.BLOCKED_DUPLICATE,
        }
    ),
    CandidateState.DEFERRED: frozenset(
        {
            CandidateState.REVIEW_READY,
            CandidateState.APPROVED,
            CandidateState.REJECTED,
            CandidateState.BLOCKED_DUPLICATE,
        }
    ),
    CandidateState.APPROVED: frozenset(
        {
            CandidateState.PUBLISHED,
            CandidateState.REVIEW_READY,
            CandidateState.BLOCKED_DUPLICATE,
        }
    ),
    CandidateState.REJECTED: frozenset(),
    CandidateState.BLOCKED_DUPLICATE: frozenset({CandidateState.REVIEW_READY}),
    CandidateState.PUBLISHED: frozenset(),
}


class DomainModel(BaseModel):
    """Base model with deterministic JSON-friendly serialization defaults."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    schema_version: Literal[1] = SCHEMA_VERSION


class SourceRecord(DomainModel):
    id: str = Field(min_length=1)
    source_type: SourceType
    url: str = Field(min_length=1)
    ownership: OwnershipStatus
    enabled: bool = True
    evidence: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SourceItem(DomainModel):
    source_id: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    description: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    author: str | None = None
    type_hint: ContributionType | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(DomainModel):
    id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_item_id: str | None = None
    url: str | None = None
    text_excerpt: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=utc_now)


class Provenance(DomainModel):
    adapter: str = Field(min_length=1)
    adapter_version: str = Field(min_length=1)
    normalizer_version: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateContribution(DomainModel):
    id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    description: str | None = None
    contribution_type: ContributionType | None = None
    date: datetime | None = None
    state: CandidateState = CandidateState.DISCOVERED
    duplicate_state: DuplicateState = DuplicateState.UNKNOWN
    ownership_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    contribution_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def transition_to(self, new_state: CandidateState) -> None:
        """Advance the candidate through the explicit lifecycle."""

        if new_state == self.state:
            return
        allowed = _ALLOWED_TRANSITIONS[self.state]
        if new_state not in allowed:
            raise DiscoveryTransitionError(
                f"Invalid candidate transition: {self.state.value} -> {new_state.value}"
            )
        self.state = new_state
        self.updated_at = utc_now()


class ReviewDecision(DomainModel):
    candidate_id: str = Field(min_length=1)
    decision: ReviewDecisionType
    reason: str | None = None
    edited_fields: dict[str, Any] = Field(default_factory=dict)
    decided_at: datetime = Field(default_factory=utc_now)


class DiscoveryRun(DomainModel):
    id: str = Field(min_length=1)
    status: DiscoveryRunStatus = DiscoveryRunStatus.RUNNING
    source_ids: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
