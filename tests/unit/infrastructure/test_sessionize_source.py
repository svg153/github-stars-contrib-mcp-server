"""Sessionize public adapter tests."""

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
from github_stars_contrib_mcp.domain.ports.source_adapter import CapabilityStatus
from github_stars_contrib_mcp.infrastructure.adapters.sessionize_source import (
    SessionizeSourceAdapter,
)
from github_stars_contrib_mcp.models import ContributionType


class FakeFetcher:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.requests: list[SafeFetchRequest] = []

    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        self.requests.append(request)
        text = json.dumps(self.payload)
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type="application/json",
            text=text,
            byte_count=len(text.encode()),
        )


PAYLOAD = {
    "eventName": "GitHub Community Day",
    "speakers": [
        {
            "id": "speaker-1",
            "fullName": "Sergio Valverde",
            "links": [{"url": "https://github.com/svg153"}],
        },
        {"id": "speaker-2", "fullName": "Other Speaker"},
    ],
    "categories": [
        {
            "id": 1,
            "title": "Session format",
            "items": [{"id": 10, "name": "Workshop"}],
        }
    ],
    "sessions": [
        {
            "id": "session-1",
            "title": "Agentic GitHub workflows",
            "description": "A practical workshop",
            "startsAt": "2026-09-06T10:00:00Z",
            "endsAt": "2026-09-06T11:00:00Z",
            "speakers": ["speaker-1"],
            "categoryItems": [10],
            "recordingUrl": "https://video.example/session-1",
            "status": "Accepted",
        },
        {
            "id": "session-2",
            "title": "Unrelated talk",
            "speakers": ["speaker-2"],
        },
    ],
}


async def test_sessionize_emits_only_verified_speaker_sessions_and_is_incremental() -> None:
    fetcher = FakeFetcher(PAYLOAD)
    adapter = SessionizeSourceAdapter(fetcher)
    source = SourceRecord(
        id="sessionize:https://sessionize.com/api/v2/event/view/All",
        source_type=SourceType.SESSIONIZE,
        url="https://sessionize.com/api/v2/event/view/All",
        ownership=OwnershipStatus.VERIFIED,
        metadata={
            "verified_speaker_ids": ["speaker-1"],
            "public_event_url": "https://sessionize.com/event",
        },
    )

    first = [batch async for batch in adapter.iter_items(source, None)][0]
    second = [batch async for batch in adapter.iter_items(source, first.next_cursor)][0]

    assert len(first.emissions) == 1
    emission = first.emissions[0]
    assert emission.item.title == "Agentic GitHub workflows"
    assert emission.item.type_hint is ContributionType.SPEAKING
    assert emission.item.metadata["session_format"] == "workshop"
    assert emission.item.metadata["recording_url"] == "https://video.example/session-1"
    assert len(second.emissions) == 0
    assert len(fetcher.requests) == 2


def test_sessionize_requires_verified_speaker_identity() -> None:
    adapter = SessionizeSourceAdapter(FakeFetcher(PAYLOAD))
    source = SourceRecord(
        id="sessionize:https://sessionize.com/api/v2/event/view/All",
        source_type=SourceType.SESSIONIZE,
        url="https://sessionize.com/api/v2/event/view/All",
        ownership=OwnershipStatus.EXPLICIT,
    )

    assert adapter.capabilities(source).status is CapabilityStatus.UNAVAILABLE
