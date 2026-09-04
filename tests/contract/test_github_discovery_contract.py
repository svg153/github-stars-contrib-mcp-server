"""GitHub REST -> eligibility -> orchestrator -> SQLite contract."""

from __future__ import annotations

import httpx
import pytest

from github_stars_contrib_mcp.di.discovery import build_discovery_runtime
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.infrastructure.adapters.github_source import (
    GitHubSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)


@pytest.mark.asyncio
async def test_github_release_contract_is_explainable_and_idempotent(tmp_path) -> None:
    release_etag = '"release-contract-v1"'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/alice/repos":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 10,
                        "node_id": "R_10",
                        "full_name": "alice/project",
                        "html_url": "https://github.com/alice/project",
                        "owner": {"login": "alice"},
                        "fork": False,
                        "archived": False,
                    }
                ],
            )
        if request.url.path == "/repos/alice/project/releases":
            if request.headers.get("if-none-match") == release_etag:
                return httpx.Response(
                    304,
                    headers={
                        "ETag": release_etag,
                        "X-RateLimit-Remaining": "4998",
                    },
                )
            return httpx.Response(
                200,
                headers={
                    "ETag": release_etag,
                    "X-RateLimit-Remaining": "4999",
                },
                json=[
                    {
                        "id": 99,
                        "node_id": "RE_99",
                        "name": "Version 2.0",
                        "tag_name": "v2.0.0",
                        "draft": False,
                        "html_url": "https://github.com/alice/project/releases/tag/v2.0.0",
                        "body": "Major public release",
                        "published_at": "2026-09-02T12:00:00Z",
                    }
                ],
            )
        raise AssertionError(f"unexpected request: {request.url}")

    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="github:https://github.com/alice",
        source_type=SourceType.GITHUB,
        url="https://github.com/alice",
        ownership=OwnershipStatus.EXPLICIT,
    )
    repository.upsert_source(source)
    adapter = GitHubSourceAdapter(transport=httpx.MockTransport(handler))
    runtime = build_discovery_runtime(
        repository=repository,
        adapters=(adapter,),
    )

    first_run = await runtime.orchestrator.run()
    candidates = repository.list_candidates()
    assert first_run.summary["sources_succeeded"] == 1
    assert first_run.summary["candidates_seen"] == 1
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.url == "https://github.com/alice/project/releases/tag/v2.0.0"
    assert candidate.provenance.adapter == "github"

    evidence = repository.list_evidence(candidate.id)
    assert len(evidence) == 1
    assert evidence[0].url == candidate.url
    assert evidence[0].data["reason_code"] == "owned_release"

    cursor = repository.get_cursor(source.id)
    assert cursor["release_etags"] == {"alice/project": release_etag}
    assert cursor["recent_ids"] == ["github:release:alice/project:99"]

    second_run = await runtime.orchestrator.run()
    assert second_run.summary["candidates_seen"] == 0
    assert len(repository.list_candidates()) == 1
    replay_cursor = repository.get_cursor(source.id)
    assert replay_cursor["release_etags"] == cursor["release_etags"]
    assert replay_cursor["recent_ids"] == cursor["recent_ids"]
