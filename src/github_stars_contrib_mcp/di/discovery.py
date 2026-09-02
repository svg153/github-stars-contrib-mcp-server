"""Composition helpers for the provider-neutral discovery pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from github_stars_contrib_mcp.application.discovery.orchestrator import (
    DiscoveryOrchestrator,
)
from github_stars_contrib_mcp.config.settings import Settings
from github_stars_contrib_mcp.domain.ports.content_fetcher import ContentFetcher
from github_stars_contrib_mcp.domain.ports.source_adapter import SourceAdapter
from github_stars_contrib_mcp.infrastructure.http import SafeHTTPFetcher
from github_stars_contrib_mcp.infrastructure.persistence import SQLiteDiscoveryRepository


@dataclass(slots=True)
class DiscoveryRuntime:
    repository: SQLiteDiscoveryRepository
    fetcher: ContentFetcher
    adapters: tuple[SourceAdapter, ...]
    orchestrator: DiscoveryOrchestrator


def build_discovery_runtime(
    *,
    settings: Settings | None = None,
    repository: SQLiteDiscoveryRepository | None = None,
    fetcher: ContentFetcher | None = None,
    adapters: Sequence[SourceAdapter] = (),
    db_path: str | Path | None = None,
) -> DiscoveryRuntime:
    """Build discovery services without registering any MCP tools."""

    resolved_repository = repository
    if resolved_repository is None:
        resolved_settings = settings or Settings()
        resolved_repository = SQLiteDiscoveryRepository(
            db_path or resolved_settings.discovery_db_path
        )
    resolved_fetcher = fetcher or SafeHTTPFetcher()
    resolved_adapters = tuple(adapters)
    return DiscoveryRuntime(
        repository=resolved_repository,
        fetcher=resolved_fetcher,
        adapters=resolved_adapters,
        orchestrator=DiscoveryOrchestrator(
            resolved_repository,
            resolved_adapters,
        ),
    )
