"""Protocol tests for the MCP Skills extension adapter."""

from __future__ import annotations

import hashlib
from typing import Literal

import mcp.types as types
import pytest
from mcp import Client, MCPError
from mcp.server import MCPServer

from github_stars_contrib_mcp.skills import (
    SKILLS_EXTENSION_ID,
    SkillCatalog,
    SkillsExtension,
    SkillsGetParams,
    SkillsGetResult,
    SkillsListParams,
    SkillsListResult,
)


class SkillsListRequest(types.Request[SkillsListParams, Literal["skills/list"]]):
    method: Literal["skills/list"] = "skills/list"
    params: SkillsListParams


class SkillsGetRequest(types.Request[SkillsGetParams, Literal["skills/get"]]):
    method: Literal["skills/get"] = "skills/get"
    params: SkillsGetParams


def _server(*, page_size: int = 50) -> MCPServer:
    return MCPServer(
        "Stars Skills Test",
        extensions=[SkillsExtension(SkillCatalog(), page_size=page_size)],
    )


@pytest.mark.asyncio
async def test_server_discover_advertises_resources_and_official_skills_extension() -> (
    None
):
    async with Client(_server(), raise_exceptions=True) as client:
        discovered = client.session.discover_result
        assert discovered is not None
        assert discovered.capabilities.resources is not None
        assert discovered.capabilities.extensions is not None
        assert discovered.capabilities.extensions[SKILLS_EXTENSION_ID] == {}


@pytest.mark.asyncio
async def test_skills_list_is_complete_cacheable_and_paginated() -> None:
    async with Client(_server(page_size=2), raise_exceptions=True) as client:
        first = await client.session.send_request(
            SkillsListRequest(params=SkillsListParams()),
            SkillsListResult,
        )
        assert first.result_type == "complete"
        assert first.ttl_ms == 300_000
        assert first.cache_scope == "public"
        assert [skill.frontmatter["name"] for skill in first.skills] == [
            "discover-my-contributions",
            "publish-approved",
        ]
        assert first.next_cursor == "2"

        second = await client.session.send_request(
            SkillsListRequest(params=SkillsListParams(cursor=first.next_cursor)),
            SkillsListResult,
        )
        assert [skill.frontmatter["name"] for skill in second.skills] == [
            "review-candidates",
            "sync-source",
        ]
        assert second.next_cursor is None

        for entry in [*first.skills, *second.skills]:
            assert entry.uri == f"skill://{entry.frontmatter['name']}/SKILL.md"
            assert entry.resources
            assert any(resource.uri == entry.uri for resource in entry.resources)
            assert all(
                resource.digest.startswith("sha256:") for resource in entry.resources
            )
            assert all(resource.size > 0 for resource in entry.resources)


@pytest.mark.asyncio
async def test_skills_get_supports_direct_lookup_without_listing() -> None:
    uri = "skill://discover-my-contributions/SKILL.md"
    async with Client(_server(), raise_exceptions=True) as client:
        result = await client.session.send_request(
            SkillsGetRequest(params=SkillsGetParams(uri=uri)),
            SkillsGetResult,
        )

        assert result.result_type == "complete"
        assert result.skill.uri == uri
        assert result.skill.frontmatter["name"] == "discover-my-contributions"
        assert result.skill.frontmatter["description"]
        assert result.ttl_ms == 300_000
        assert result.cache_scope == "public"


@pytest.mark.asyncio
async def test_resources_read_is_lazy_and_matches_advertised_manifest_bytes() -> None:
    uri = "skill://discover-my-contributions/SKILL.md"
    async with Client(_server(), raise_exceptions=True) as client:
        skill_result = await client.session.send_request(
            SkillsGetRequest(params=SkillsGetParams(uri=uri)),
            SkillsGetResult,
        )
        [manifest] = [
            resource for resource in skill_result.skill.resources if resource.uri == uri
        ]

        read_result = await client.read_resource(uri)
        assert read_result.result_type == "complete"
        assert len(read_result.contents) == 1
        contents = read_result.contents[0]
        assert isinstance(contents, types.TextResourceContents)
        assert contents.uri == uri
        assert contents.mime_type == "text/markdown"
        raw = contents.text.encode("utf-8")
        assert len(raw) == manifest.size
        assert f"sha256:{hashlib.sha256(raw).hexdigest()}" == manifest.digest
        assert contents.text.startswith("---\nname: discover-my-contributions\n")


@pytest.mark.asyncio
async def test_unknown_skill_and_invalid_cursor_are_invalid_params() -> None:
    async with Client(_server(page_size=2), raise_exceptions=True) as client:
        with pytest.raises(MCPError) as unknown:
            await client.session.send_request(
                SkillsGetRequest(
                    params=SkillsGetParams(uri="skill://missing/SKILL.md")
                ),
                SkillsGetResult,
            )
        assert unknown.value.code == types.INVALID_PARAMS

        with pytest.raises(MCPError) as invalid_cursor:
            await client.session.send_request(
                SkillsListRequest(params=SkillsListParams(cursor="not-a-cursor")),
                SkillsListResult,
            )
        assert invalid_cursor.value.code == types.INVALID_PARAMS


@pytest.mark.asyncio
async def test_unknown_skill_resource_uses_base_resources_invalid_params_path() -> None:
    async with Client(_server(), raise_exceptions=True) as client:
        with pytest.raises(MCPError) as unknown:
            await client.read_resource("skill://missing/SKILL.md")
        assert unknown.value.code == types.INVALID_PARAMS
