from datetime import UTC, datetime

import pytest

from github_stars_contrib_mcp.application.discovery.deduplicator import (
    Deduplicator,
    load_stars_snapshot,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    DuplicateState,
    Provenance,
)
from github_stars_contrib_mcp.models import ContributionType


class FakeStars:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def list_contributions(self, page=1):
        self.calls.append(page)
        return self.pages[page - 1]


class BrokenStars:
    async def list_contributions(self, page=1):
        raise RuntimeError("offline")


def candidate(
    *,
    cid="c1",
    source="s1",
    external="e1",
    url="https://example.com/talk",
    title="Talk",
):
    return CandidateContribution(
        id=cid,
        source_id=source,
        external_id=external,
        title=title,
        url=url,
        contribution_type=ContributionType.SPEAKING,
        date=datetime(2026, 9, 1, tzinfo=UTC),
        provenance=Provenance(adapter="test", adapter_version="1"),
    )


@pytest.mark.asyncio
async def test_snapshot_paginates_once() -> None:
    api = FakeStars(
        [
            {"data": [{"id": "1"}], "pagination": {"totalPages": 2}},
            {"data": [{"id": "2"}], "pagination": {"totalPages": 2}},
        ]
    )
    snapshot = await load_stars_snapshot(api)
    assert snapshot.available is True
    assert [row["id"] for row in snapshot.contributions] == ["1", "2"]
    assert api.calls == [1, 2]


@pytest.mark.asyncio
async def test_unavailable_stars_yields_unknown() -> None:
    snapshot = await load_stars_snapshot(BrokenStars())
    match, _ = Deduplicator(snapshot).assess(candidate(), [])
    assert snapshot.available is False
    assert match.state is DuplicateState.UNKNOWN


@pytest.mark.asyncio
async def test_exact_stars_url_blocks_even_with_tracking_difference() -> None:
    api = FakeStars(
        [
            {
                "data": [
                    {"id": "42", "url": "https://example.com/talk", "title": "Other"}
                ],
                "pagination": {"totalPages": 1},
            }
        ]
    )
    snapshot = await load_stars_snapshot(api)
    match, _ = Deduplicator(snapshot).assess(
        candidate(url="https://example.com/talk?utm_source=newsletter"), []
    )
    assert match.state is DuplicateState.EXACT
    assert match.method == "canonical_url"


@pytest.mark.asyncio
async def test_likely_match_is_not_exact() -> None:
    api = FakeStars(
        [
            {
                "data": [
                    {
                        "id": "42",
                        "url": "https://mirror.example/talk",
                        "title": " talk ",
                        "date": "2026-09-02",
                        "type": "SPEAKING",
                    }
                ],
                "pagination": {"totalPages": 1},
            }
        ]
    )
    snapshot = await load_stars_snapshot(api)
    match, _ = Deduplicator(snapshot).assess(candidate(), [])
    assert match.state is DuplicateState.LIKELY


@pytest.mark.asyncio
async def test_same_run_local_url_is_exact_duplicate() -> None:
    snapshot = await load_stars_snapshot(
        FakeStars([{"data": [], "pagination": {"totalPages": 1}}])
    )
    first = candidate(cid="one", source="a", external="1")
    second = candidate(cid="two", source="b", external="2")
    match, _ = Deduplicator(snapshot).assess(second, [first])
    assert match.state is DuplicateState.EXACT
    assert match.target == "one"
