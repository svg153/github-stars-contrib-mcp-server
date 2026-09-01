"""Tests for deterministic discovery source identity."""

import pytest

from github_stars_contrib_mcp.application.discovery.source_identity import (
    canonical_origin,
    canonicalize_source_url,
)
from github_stars_contrib_mcp.domain.discovery import SourceType


def test_canonicalizes_equivalent_github_urls() -> None:
    left = canonicalize_source_url(
        "HTTPS://WWW.GITHUB.COM:443/svg153/repo/?utm_source=test#readme"
    )
    right = canonicalize_source_url("https://github.com/svg153/repo")

    assert left == right
    assert left.source_type is SourceType.GITHUB


def test_normalizes_social_aliases_and_tracking_query() -> None:
    source = canonicalize_source_url(
        "https://twitter.com/svg153/?b=2&utm_medium=social&a=1"
    )

    assert source.canonical_url == "https://x.com/svg153?a=1&b=2"
    assert source.source_type is SourceType.X


def test_classifies_feed_and_missing_scheme() -> None:
    feed = canonicalize_source_url("Example.COM/feed/")
    assert feed.canonical_url == "https://example.com/feed"
    assert feed.source_type is SourceType.RSS


def test_origin_removes_contribution_path_and_query() -> None:
    origin = canonical_origin(
        "https://blog.example.com/posts/one?utm_source=stars&ref=profile"
    )
    assert origin.canonical_url == "https://blog.example.com"
    assert origin.source_id == "website:https://blog.example.com"


@pytest.mark.parametrize("url", ["", "ftp://example.com/file", "http://example.com:bad"])
def test_rejects_invalid_source_urls(url: str) -> None:
    with pytest.raises(ValueError):
        canonicalize_source_url(url)
