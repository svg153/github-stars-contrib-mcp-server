"""Repository ports for local contribution discovery state."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Any, Protocol, runtime_checkable

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    Evidence,
    ReviewDecision,
    SourceRecord,
)


@runtime_checkable
class SourceRepository(Protocol):
    def get_source(self, source_id: str) -> SourceRecord | None: ...

    def list_sources(self, *, enabled_only: bool = False) -> list[SourceRecord]: ...

    def upsert_source(self, source: SourceRecord) -> SourceRecord: ...

    def get_cursor(self, source_id: str) -> dict[str, Any] | None: ...

    def save_cursor(self, source_id: str, cursor: dict[str, Any] | None) -> None: ...


@runtime_checkable
class CandidateRepository(Protocol):
    def get_candidate(self, candidate_id: str) -> CandidateContribution | None: ...

    def list_candidates(
        self, *, states: set[CandidateState] | None = None
    ) -> list[CandidateContribution]: ...

    def save_candidate(
        self,
        candidate: CandidateContribution,
        evidence: Sequence[Evidence] = (),
    ) -> CandidateContribution: ...

    def list_evidence(self, candidate_id: str) -> list[Evidence]: ...

    def record_review(self, decision: ReviewDecision) -> None: ...

    def record_publication(
        self, candidate_id: str, client_id: str, result: dict[str, Any]
    ) -> None: ...


@runtime_checkable
class DiscoveryRunRepository(Protocol):
    def save_run(self, run: DiscoveryRun) -> DiscoveryRun: ...

    def get_run(self, run_id: str) -> DiscoveryRun | None: ...


@runtime_checkable
class DiscoveryUnitOfWork(Protocol):
    def transaction(self) -> AbstractContextManager[None]: ...
