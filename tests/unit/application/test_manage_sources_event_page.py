"""Explicit event-page source registration tests."""

import pytest

from github_stars_contrib_mcp.application.use_cases.manage_sources import ManageSources
from github_stars_contrib_mcp.domain.discovery import SourceType
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)


def test_event_page_source_type_requires_explicit_override(tmp_path) -> None:
    manager = ManageSources(SQLiteDiscoveryRepository(tmp_path / "discovery.db"))

    source = manager.add(
        "https://events.example/session/42",
        source_type=SourceType.EVENT_PAGE,
        metadata={"verified_speaker_names": ["Sergio Valverde"]},
    )

    assert source.source_type is SourceType.EVENT_PAGE
    assert source.id == "event_page:https://events.example/session/42"


def test_provider_type_cannot_be_overridden_arbitrarily(tmp_path) -> None:
    manager = ManageSources(SQLiteDiscoveryRepository(tmp_path / "discovery.db"))

    with pytest.raises(ValueError, match="explicit event pages"):
        manager.add("https://example.com", source_type=SourceType.GITHUB)
