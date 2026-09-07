from datetime import UTC, datetime

from github_stars_contrib_mcp.application.discovery.fingerprint import (
    canonicalize_url,
    fingerprint_candidate,
)
from github_stars_contrib_mcp.domain.discovery import CandidateContribution, Provenance
from github_stars_contrib_mcp.models import ContributionType


def candidate(url: str, title: str = "  My   Talk ") -> CandidateContribution:
    return CandidateContribution(
        id="candidate:1",
        source_id="youtube:me",
        external_id="abc",
        title=title,
        url=url,
        contribution_type=ContributionType.SPEAKING,
        date=datetime(2026, 9, 1, 10, tzinfo=UTC),
        provenance=Provenance(adapter="test", adapter_version="1"),
    )


def test_canonical_url_removes_tracking_fragment_and_normalizes_order() -> None:
    a = canonicalize_url("HTTPS://Example.COM/talk/?b=2&utm_source=x&a=1#section")
    b = canonicalize_url("https://example.com/talk?a=1&b=2")
    assert a == b


def test_separate_fingerprints_keep_identity_explainable() -> None:
    first = fingerprint_candidate(candidate("https://example.com/talk?utm_source=x"))
    second = fingerprint_candidate(candidate("https://example.com/talk", "my talk"))
    assert first.source == second.source
    assert first.url == second.url
    assert first.content == second.content
    assert first.source != first.url


def test_content_fingerprint_requires_structured_date_and_type() -> None:
    item = candidate("https://example.com/talk")
    item.date = None
    assert fingerprint_candidate(item).content is None
