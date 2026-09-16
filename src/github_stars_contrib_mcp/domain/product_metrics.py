"""Privacy-safe product metric facts derived from local discovery state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CandidateMetricFact:
    source_type: str
    adapter: str
    contribution_type: str
    state: str
    duplicate_state: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewMetricFact:
    decision: str
    edited: bool
    source_type: str
    adapter: str
    contribution_type: str
    candidate_created_at: datetime
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class RunSourceMetricFact:
    source_type: str
    adapter: str
    capability: str
    status: str
    error_kind: str
    candidate_count: int


@dataclass(frozen=True, slots=True)
class RunMetricFact:
    status: str
    dry_run: bool
    candidates_seen: int
    source_count: int
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProductMetricsSnapshot:
    candidates: tuple[CandidateMetricFact, ...] = ()
    review_actions: tuple[ReviewMetricFact, ...] = ()
    latest_reviews: tuple[ReviewMetricFact, ...] = ()
    first_reviews: tuple[ReviewMetricFact, ...] = ()
    run_sources: tuple[RunSourceMetricFact, ...] = ()
    runs: tuple[RunMetricFact, ...] = ()
