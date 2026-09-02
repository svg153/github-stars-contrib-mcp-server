"""Tests for source bootstrap from existing Stars data."""

from copy import deepcopy
from typing import Any

import pytest

from github_stars_contrib_mcp.application.use_cases.bootstrap_sources import (
    BootstrapSources,
)
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)


class FakeStarsAPI:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls = 0

    async def get_user_data(self) -> dict[str, Any]:
        self.calls += 1
        return deepcopy(self.payload)


class FakeSourceRepository:
    def __init__(self) -> None:
        self.items: dict[str, SourceRecord] = {}

    def get_source(self, source_id: str) -> SourceRecord | None:
        item = self.items.get(source_id)
        return item.model_copy(deep=True) if item else None

    def list_sources(self, *, enabled_only: bool = False) -> list[SourceRecord]:
        values = list(self.items.values())
        if enabled_only:
            values = [item for item in values if item.enabled]
        return [item.model_copy(deep=True) for item in values]

    def upsert_source(self, source: SourceRecord) -> SourceRecord:
        self.items[source.id] = source.model_copy(deep=True)
        return source


@pytest.fixture
def stars_payload() -> dict[str, Any]:
    return {
        "loggedUser": {
            "nominee": {
                "links": [
                    {
                        "id": "link-blog",
                        "link": "https://blog.example.com/",
                        "platform": "WEBSITE",
                    },
                    {
                        "id": "link-youtube",
                        "link": "https://www.youtube.com/@example",
                        "platform": "YOUTUBE",
                    },
                ],
                "contributions": [
                    {"id": "post-1", "url": "https://blog.example.com/posts/1"},
                    {"id": "post-2", "url": "https://blog.example.com/posts/2"},
                    {"id": "other-1", "url": "https://writing.example.net/one"},
                    {"id": "other-2", "url": "https://writing.example.net/two"},
                    {"id": "youtube-video", "url": "https://youtube.com/watch?v=abc"},
                ],
            }
        }
    }


@pytest.mark.asyncio
async def test_bootstrap_uses_profile_links_and_repeated_personal_domains(
    stars_payload: dict[str, Any],
) -> None:
    repository = FakeSourceRepository()
    api = FakeStarsAPI(stars_payload)

    result = await BootstrapSources(api, repository)()

    blog = repository.items["website:https://blog.example.com"]
    inferred = repository.items["website:https://writing.example.net"]
    youtube = repository.items["youtube:https://youtube.com/@example"]

    assert blog.ownership is OwnershipStatus.EXPLICIT
    assert set(blog.metadata["bootstrap"]["contribution_ids"]) == {"post-1", "post-2"}
    assert inferred.ownership is OwnershipStatus.INFERRED
    assert inferred.metadata["bootstrap"]["contribution_count"] == 2
    assert youtube.ownership is OwnershipStatus.EXPLICIT
    assert "youtube:https://youtube.com" not in repository.items
    assert result.sources
    assert api.calls == 1


@pytest.mark.asyncio
async def test_bootstrap_is_state_idempotent(stars_payload: dict[str, Any]) -> None:
    repository = FakeSourceRepository()
    use_case = BootstrapSources(FakeStarsAPI(stars_payload), repository)

    await use_case()
    first = {
        key: item.model_dump(mode="json") for key, item in repository.items.items()
    }
    second = await use_case()
    after = {
        key: item.model_dump(mode="json") for key, item in repository.items.items()
    }

    assert after == first
    assert second.created == 0
    assert second.updated == 0


@pytest.mark.asyncio
async def test_bootstrap_never_downgrades_verified_or_rejected_sources(
    stars_payload: dict[str, Any],
) -> None:
    repository = FakeSourceRepository()
    repository.items["website:https://blog.example.com"] = SourceRecord(
        id="website:https://blog.example.com",
        source_type=SourceType.WEBSITE,
        url="https://blog.example.com",
        ownership=OwnershipStatus.VERIFIED,
    )
    repository.items["youtube:https://youtube.com/@example"] = SourceRecord(
        id="youtube:https://youtube.com/@example",
        source_type=SourceType.YOUTUBE,
        url="https://youtube.com/@example",
        ownership=OwnershipStatus.REJECTED,
        enabled=False,
    )

    await BootstrapSources(FakeStarsAPI({"data": stars_payload}), repository)()

    assert (
        repository.items["website:https://blog.example.com"].ownership
        is OwnershipStatus.VERIFIED
    )
    rejected = repository.items["youtube:https://youtube.com/@example"]
    assert rejected.ownership is OwnershipStatus.REJECTED
    assert rejected.enabled is False
