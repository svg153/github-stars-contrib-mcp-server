"""Contract-shape tests for discovery repository ports."""

from contextlib import contextmanager
from typing import Any

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    Evidence,
    ReviewDecision,
    SourceRecord,
)
from github_stars_contrib_mcp.domain.ports.discovery_repository import (
    CandidateRepository,
    DiscoveryRunRepository,
    DiscoveryUnitOfWork,
    SourceRepository,
)


class InMemoryDiscoveryRepository:
    def get_source(self, source_id: str) -> SourceRecord | None:
        return None

    def list_sources(self, *, enabled_only: bool = False) -> list[SourceRecord]:
        return []

    def upsert_source(self, source: SourceRecord) -> SourceRecord:
        return source

    def get_cursor(self, source_id: str) -> dict[str, Any] | None:
        return None

    def save_cursor(self, source_id: str, cursor: dict[str, Any] | None) -> None:
        return None

    def get_candidate(self, candidate_id: str) -> CandidateContribution | None:
        return None

    def list_candidates(
        self, *, states: set[CandidateState] | None = None
    ) -> list[CandidateContribution]:
        return []

    def save_candidate(
        self,
        candidate: CandidateContribution,
        evidence: tuple[Evidence, ...] = (),
    ) -> CandidateContribution:
        return candidate

    def list_evidence(self, candidate_id: str) -> list[Evidence]:
        return []

    def record_review(self, decision: ReviewDecision) -> None:
        return None

    def record_publication(
        self, candidate_id: str, client_id: str, result: dict[str, Any]
    ) -> None:
        return None

    def save_run(self, run: DiscoveryRun) -> DiscoveryRun:
        return run

    def get_run(self, run_id: str) -> DiscoveryRun | None:
        return None

    @contextmanager
    def transaction(self):
        yield


def test_repository_ports_are_provider_neutral_runtime_contracts() -> None:
    repository = InMemoryDiscoveryRepository()

    assert isinstance(repository, SourceRepository)
    assert isinstance(repository, CandidateRepository)
    assert isinstance(repository, DiscoveryRunRepository)
    assert isinstance(repository, DiscoveryUnitOfWork)
