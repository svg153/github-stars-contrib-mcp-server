"""Pretalx public adapter tests."""

import json

from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    FetchOutcome,
    FetchSecurityClassification,
    SafeFetchRequest,
    SafeFetchResult,
)
from github_stars_contrib_mcp.infrastructure.adapters.pretalx_source import (
    PretalxSourceAdapter,
)
from github_stars_contrib_mcp.models import ContributionType


class FakeFetcher:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.requests: list[SafeFetchRequest] = []

    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        self.requests.append(request)
        text = json.dumps(self.responses[request.url])
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type="application/json",
            text=text,
            byte_count=len(text.encode()),
        )


SUBMISSIONS = {
    "results": [
        {
            "code": "ABC123",
            "title": "Shipping safer agentic workflows",
            "abstract": "Practical patterns",
            "speakers": [{"code": "SPK1", "name": "Sergio Valverde"}],
            "submission_type": {"name": "Talk"},
            "state": "confirmed",
        },
        {
            "code": "OTHER",
            "title": "Another session",
            "speakers": [{"code": "SPK2", "name": "Other Speaker"}],
        },
    ]
}
SCHEDULE = {
    "results": [
        {
            "submission": "ABC123",
            "start": "2026-09-07T09:00:00Z",
            "end": "2026-09-07T09:45:00Z",
            "room": "Main",
        }
    ]
}


async def test_pretalx_matches_stable_speaker_id_and_preserves_schedule_updates() -> None:
    submissions_url = "https://pretalx.example/api/events/conf/submissions/"
    schedule_url = "https://pretalx.example/api/events/conf/schedule/"
    fetcher = FakeFetcher({submissions_url: SUBMISSIONS, schedule_url: SCHEDULE})
    adapter = PretalxSourceAdapter(fetcher)
    source = SourceRecord(
        id=f"pretalx:{submissions_url}",
        source_type=SourceType.PRETALX,
        url=submissions_url,
        ownership=OwnershipStatus.VERIFIED,
        metadata={
            "verified_speaker_ids": ["SPK1"],
            "schedule_url": schedule_url,
            "event_name": "FOSS Conference",
            "public_event_url": "https://pretalx.example/conf",
        },
    )

    first = [batch async for batch in adapter.iter_items(source, None)][0]
    assert len(first.emissions) == 1
    item = first.emissions[0].item
    assert item.type_hint is ContributionType.SPEAKING
    assert item.url == "https://pretalx.example/conf/talk/ABC123/"
    assert item.published_at is not None

    second = [batch async for batch in adapter.iter_items(source, first.next_cursor)][0]
    assert len(second.emissions) == 0

    fetcher.responses[schedule_url] = {
        "results": [
            {
                "submission": "ABC123",
                "start": "2026-09-07T10:00:00Z",
                "end": "2026-09-07T10:45:00Z",
                "room": "Main",
            }
        ]
    }
    updated = [batch async for batch in adapter.iter_items(source, first.next_cursor)][0]
    assert len(updated.emissions) == 1
    assert updated.emissions[0].item.published_at.hour == 10
