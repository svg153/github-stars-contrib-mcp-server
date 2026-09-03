"""Offline RSS/Atom parser tests."""

from pathlib import Path

import pytest

from github_stars_contrib_mcp.infrastructure.adapters.feed_parser import (
    FeedParseError,
    parse_feed,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "discovery" / "feeds"


def test_parse_rss_keeps_valid_entries_and_item_level_errors() -> None:
    parsed = parse_feed((FIXTURES / "rss.xml").read_bytes())

    assert [entry.stable_id for entry in parsed.entries] == ["post-1", "post-2"]
    assert parsed.entries[0].title == "First & useful post"
    assert parsed.entries[0].summary == "First summary ."
    assert parsed.entries[0].author == "Sergio"
    assert parsed.entries[0].published_at is not None
    assert len(parsed.errors) == 2
    assert "missing title" in parsed.errors[0]
    assert "duplicate stable id" in parsed.errors[1]


def test_parse_atom_extracts_structured_fields() -> None:
    parsed = parse_feed((FIXTURES / "atom.xml").read_text())

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert entry.stable_id == "tag:example.com,2026:atom-1"
    assert entry.link == "https://example.com/atom/1"
    assert entry.author == "Sergio"
    assert entry.summary == "Atom summary"
    assert entry.published_at is not None
    assert entry.updated_at is not None


@pytest.mark.parametrize(
    "payload",
    [
        "<rss><channel>",
        '<!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><rss/>',
    ],
)
def test_parse_feed_rejects_unsafe_or_malformed_documents(payload: str) -> None:
    with pytest.raises(FeedParseError):
        parse_feed(payload)
