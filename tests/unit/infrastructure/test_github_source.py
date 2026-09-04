"""Offline tests for the GitHub REST discovery adapter."""

from __future__ import annotations

import httpx
import pytest

from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterErrorKind,
    CapabilityStatus,
    SourceAdapterError,
)
from github_stars_contrib_mcp.infrastructure.adapters.github_source import (
    GITHUB_API_VERSION,
    GitHubSourceAdapter,
)


def _source(**metadata) -> SourceRecord:
    return SourceRecord(
        id="github:https://github.com/alice",
        source_type=SourceType.GITHUB,
        url="https://github.com/alice",
        ownership=OwnershipStatus.EXPLICIT,
        metadata=metadata,
    )


def _repo(name: str, repo_id: int) -> dict:
    return {
        "id": repo_id,
        "node_id": f"R_{repo_id}",
        "full_name": f"alice/{name}",
        "html_url": f"https://github.com/alice/{name}",
        "owner": {"login": "alice"},
        "fork": False,
        "archived": False,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-09-01T00:00:00Z",
        "description": f"{name} project",
    }


async def _collect(adapter: GitHubSourceAdapter, source: SourceRecord, cursor=None):
    return [batch async for batch in adapter.iter_items(source, cursor)]


def test_capability_is_limited_without_token_and_available_with_token() -> None:
    source = _source()
    limited = GitHubSourceAdapter().capabilities(source)
    available = GitHubSourceAdapter(token="github-token").capabilities(source)
    assert limited.status is CapabilityStatus.LIMITED
    assert available.status is CapabilityStatus.AVAILABLE


@pytest.mark.asyncio
async def test_paginates_owned_repositories_and_uses_current_api_headers() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/users/alice/repos" and request.url.params.get("page") == "2":
            return httpx.Response(200, json=[_repo("two", 2)])
        if request.url.path == "/users/alice/repos":
            return httpx.Response(
                200,
                json=[_repo("one", 1)],
                headers={
                    "Link": '<https://api.github.com/users/alice/repos?page=2>; rel="next"',
                    "X-RateLimit-Remaining": "4999",
                },
            )
        if request.url.path.endswith("/releases"):
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected request: {request.url}")

    adapter = GitHubSourceAdapter(
        token="github-token",
        transport=httpx.MockTransport(handler),
    )
    batches = await _collect(adapter, _source(include_repositories=True))

    assert len(batches) == 1
    assert {emission.item.title for emission in batches[0].emissions} == {
        "alice/one",
        "alice/two",
    }
    assert requests[0].headers["x-github-api-version"] == GITHUB_API_VERSION
    assert requests[0].headers["authorization"] == "Bearer github-token"


@pytest.mark.asyncio
async def test_release_uses_etag_cursor_and_replay_emits_no_duplicate() -> None:
    release_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/alice/repos":
            return httpx.Response(200, json=[_repo("project", 1)])
        if request.url.path == "/repos/alice/project/releases":
            release_requests.append(request)
            if request.headers.get("if-none-match") == '"release-v1"':
                return httpx.Response(
                    304,
                    headers={
                        "ETag": '"release-v1"',
                        "X-RateLimit-Remaining": "4998",
                    },
                )
            return httpx.Response(
                200,
                headers={
                    "ETag": '"release-v1"',
                    "X-RateLimit-Remaining": "4999",
                },
                json=[
                    {
                        "id": 77,
                        "node_id": "RE_77",
                        "name": "Version 1.0",
                        "tag_name": "v1.0.0",
                        "draft": False,
                        "html_url": "https://github.com/alice/project/releases/tag/v1.0.0",
                        "body": "First stable release",
                        "created_at": "2026-09-01T10:00:00Z",
                        "published_at": "2026-09-01T11:00:00Z",
                    }
                ],
            )
        raise AssertionError(f"unexpected request: {request.url}")

    adapter = GitHubSourceAdapter(transport=httpx.MockTransport(handler))
    source = _source()
    first = (await _collect(adapter, source))[0]
    second = (await _collect(adapter, source, first.next_cursor))[0]

    assert len(first.emissions) == 1
    emission = first.emissions[0]
    assert emission.item.external_id == "github:release:alice/project:77"
    assert emission.item.url == "https://github.com/alice/project/releases/tag/v1.0.0"
    assert emission.evidence[0].data["reason_code"] == "owned_release"
    assert first.next_cursor["release_etags"] == {
        "alice/project": '"release-v1"'
    }
    assert second.emissions == ()
    assert release_requests[-1].headers["if-none-match"] == '"release-v1"'


@pytest.mark.asyncio
async def test_rate_limit_is_classified() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "0"},
            json={"message": "rate limit"},
        )

    adapter = GitHubSourceAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(SourceAdapterError) as exc_info:
        await _collect(adapter, _source())
    assert exc_info.value.kind is AdapterErrorKind.RATE_LIMIT


@pytest.mark.asyncio
async def test_explicit_auth_failure_marks_capability_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "bad credentials"})

    adapter = GitHubSourceAdapter(
        token="bad-token",
        transport=httpx.MockTransport(handler),
    )
    source = _source()
    with pytest.raises(SourceAdapterError) as exc_info:
        await _collect(adapter, source)

    assert exc_info.value.kind is AdapterErrorKind.AUTH
    capability = adapter.capabilities(source)
    assert capability.status is CapabilityStatus.UNAVAILABLE
    assert capability.requires_credentials is True


@pytest.mark.asyncio
async def test_only_explicit_notable_paths_become_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/alice/repos":
            return httpx.Response(200, json=[])
        if request.url.path == "/repos/alice/project/pulls/12":
            return httpx.Response(
                200,
                json={
                    "id": 12,
                    "node_id": "PR_12",
                    "title": "Large platform migration",
                    "body": "Substantial migration work",
                    "html_url": "https://github.com/alice/project/pull/12",
                    "user": {"login": "alice"},
                    "created_at": "2026-08-01T00:00:00Z",
                    "updated_at": "2026-08-02T00:00:00Z",
                },
            )
        raise AssertionError(f"unexpected request: {request.url}")

    adapter = GitHubSourceAdapter(transport=httpx.MockTransport(handler))
    source = _source(
        notable_api_paths=[
            "/repos/alice/project/pulls/12",
            "/users/alice/events",
        ]
    )
    batch = (await _collect(adapter, source))[0]

    assert len(batch.emissions) == 1
    assert batch.emissions[0].evidence[0].data["reason_code"] == (
        "configured_notable_activity"
    )
