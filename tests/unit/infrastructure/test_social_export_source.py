"""Restricted social exports are local-only, versioned and deterministic."""

import json

import pytest

from github_stars_contrib_mcp.domain.discovery import OwnershipStatus, SourceRecord, SourceType
from github_stars_contrib_mcp.domain.ports.source_adapter import SourceAdapterError
from github_stars_contrib_mcp.infrastructure.adapters.social_export_source import (
    SocialExportSourceAdapter,
)
from github_stars_contrib_mcp.models import ContributionType


def _source(source_type: SourceType, import_path: str) -> SourceRecord:
    return SourceRecord(
        id=f"{source_type.value}:profile",
        source_type=source_type,
        url=(
            "https://x.com/alice"
            if source_type is SourceType.X
            else "https://linkedin.com/in/alice"
        ),
        ownership=OwnershipStatus.EXPLICIT,
        metadata={"social_mode": "export_import", "import_path": import_path},
    )


@pytest.mark.asyncio
async def test_json_import_is_local_only_and_idempotent(tmp_path) -> None:
    path = tmp_path / "posts.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provider": "x",
                "posts": [
                    {
                        "id": "123",
                        "url": "https://twitter.com/alice/status/123",
                        "title": "Launch",
                        "text": "Public launch note",
                        "published_at": "2026-09-07T10:00:00Z",
                        "contribution_type": "OTHER",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source = _source(SourceType.X, str(path))
    adapter = SocialExportSourceAdapter()
    first = [batch async for batch in adapter.iter_items(source, None)][0]
    emission = first.emissions[0]

    assert emission.item.external_id == "x:123"
    assert emission.item.url == "https://x.com/alice/status/123"
    assert emission.item.type_hint is ContributionType.OTHER
    assert emission.evidence[0].data["import_file"] == "posts.json"
    assert emission.evidence[0].data["network_fetch"] is False
    assert emission.evidence[0].data["uploaded"] is False

    replay = [
        batch async for batch in adapter.iter_items(source, first.next_cursor)
    ][0]
    assert replay.emissions == ()


@pytest.mark.asyncio
async def test_csv_linkedin_import_uses_versioned_neutral_schema(tmp_path) -> None:
    path = tmp_path / "linkedin.csv"
    path.write_text(
        "schema_version,provider,id,url,title,text,published_at,author,contribution_type\n"
        "1,linkedin,456,https://www.linkedin.com/feed/update/urn:li:activity:456,Post,Text,2026-09-07T11:00:00Z,alice,OTHER\n",
        encoding="utf-8",
    )
    source = _source(SourceType.LINKEDIN, str(path))
    batch = [
        batch async for batch in SocialExportSourceAdapter().iter_items(source, None)
    ][0]

    assert batch.emissions[0].item.external_id == "linkedin:456"
    assert batch.emissions[0].item.url.startswith("https://linkedin.com/feed/update/")


@pytest.mark.asyncio
async def test_provider_mismatch_or_non_post_url_fails_closed(tmp_path) -> None:
    path = tmp_path / "posts.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provider": "linkedin",
                "posts": [{"url": "https://linkedin.com/in/alice"}],
            }
        ),
        encoding="utf-8",
    )
    source = _source(SourceType.X, str(path))

    with pytest.raises(SourceAdapterError):
        _ = [
            batch
            async for batch in SocialExportSourceAdapter().iter_items(source, None)
        ]


def test_missing_local_file_is_actionably_unavailable(tmp_path) -> None:
    source = _source(SourceType.X, str(tmp_path / "missing.json"))
    capability = SocialExportSourceAdapter().capabilities(source)

    assert capability.user_action is not None
