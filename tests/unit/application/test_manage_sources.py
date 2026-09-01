"""Tests for explicit source registry management."""

import pytest

from github_stars_contrib_mcp.application.use_cases.manage_sources import ManageSources
from github_stars_contrib_mcp.domain.discovery import OwnershipStatus
from github_stars_contrib_mcp.infrastructure.persistence import SQLiteDiscoveryRepository


def test_add_verify_disable_preserves_cursor(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    manager = ManageSources(repository)
    source = manager.add("https://example.com/", metadata={"owner": "user"})
    repository.save_cursor(source.id, {"page": 3})

    verified = manager.verify(source.id)
    disabled = manager.disable(source.id)

    assert verified.ownership is OwnershipStatus.VERIFIED
    assert disabled.enabled is False
    assert repository.get_cursor(source.id) == {"page": 3}


def test_rejection_requires_explicit_readd_before_verify(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    manager = ManageSources(repository)
    source = manager.add("https://example.com")
    rejected = manager.reject(source.id, reason="Not mine")

    assert rejected.ownership is OwnershipStatus.REJECTED
    assert rejected.enabled is False
    with pytest.raises(ValueError, match="explicitly re-added"):
        manager.verify(source.id)

    readded = manager.add("https://example.com")
    assert readded.ownership is OwnershipStatus.EXPLICIT
    assert readded.enabled is True
    assert readded.metadata["rejection_history"][0]["reason"] == "Not mine"


def test_rejected_source_cannot_be_enabled_directly(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    manager = ManageSources(repository)
    source = manager.add("https://example.com")
    manager.reject(source.id, reason="Wrong identity")

    with pytest.raises(ValueError, match="explicitly re-added"):
        manager.enable(source.id)


def test_unknown_source_is_explicit_error(tmp_path) -> None:
    manager = ManageSources(SQLiteDiscoveryRepository(tmp_path / "discovery.db"))

    with pytest.raises(KeyError, match="Unknown source"):
        manager.disable("missing")
