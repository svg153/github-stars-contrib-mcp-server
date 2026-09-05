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
from github_stars_contrib_mcp.infrastructure.adapters.github_source import (
    GitHubSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.adapters.rss_source import RSSSourceAdapter
from github_stars_contrib_mcp.infrastructure.adapters.website_source import (
    WebsiteSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.adapters.youtube_feed_source import (
    YouTubeFeedSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.adapters.youtube_source import (
    YouTubeSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.http import SafeHTTPFetcher
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)


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
    adapters: Sequence[SourceAdapter] | None = None,
    db_path: str | Path | None = None,
) -> DiscoveryRuntime:
    """Build discovery services without registering any MCP tools."""

    resolved_settings = settings or Settings()
    resolved_repository = repository
    if resolved_repository is None:
        resolved_repository = SQLiteDiscoveryRepository(
            db_path or resolved_settings.discovery_db_path
        )
    resolved_fetcher = fetcher or SafeHTTPFetcher()
    youtube_key = resolved_settings.youtube_api_key
    youtube_adapter: SourceAdapter
    if isinstance(youtube_key, str) and youtube_key.strip():
        youtube_adapter = YouTubeSourceAdapter(api_key=youtube_key)
    else:
        youtube_adapter = YouTubeFeedSourceAdapter(resolved_fetcher)
    resolved_adapters = (
        tuple(adapters)
        if adapters is not None
        else (
            RSSSourceAdapter(resolved_fetcher),
            WebsiteSourceAdapter(resolved_fetcher),
            GitHubSourceAdapter(token=resolved_settings.github_discovery_token),
            youtube_adapter,
        )
    )
    return DiscoveryRuntime(
        repository=resolved_repository,
        fetcher=resolved_fetcher,
        adapters=resolved_adapters,
        orchestrator=DiscoveryOrchestrator(
            resolved_repository,
            resolved_adapters,
        ),
    )
