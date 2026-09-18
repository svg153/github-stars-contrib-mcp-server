"""Integration tests for prompts and completion over the MCP protocol.

These exercise the real server process spawned by the ``mcp_server`` fixture, so
they prove the prompt and completion capabilities are advertised and served to
an MCP client, not merely registered in-process.
"""

from __future__ import annotations

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import PromptReference

EXPECTED_PROMPTS = {
    "contribution_create",
    "contribution_update",
    "contributions_search",
    "contributions_stats",
    "contributions_summary",
}


@pytest.mark.asyncio
async def test_server_advertises_prompt_and_completion_capabilities(mcp_server: str):
    async with streamable_http_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.initialize()
            assert result.capabilities.prompts is not None
            assert result.capabilities.completions is not None


@pytest.mark.asyncio
async def test_list_prompts_exposes_contribution_workflows(mcp_server: str):
    async with streamable_http_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            prompts = await session.list_prompts()
            assert EXPECTED_PROMPTS <= {prompt.name for prompt in prompts.prompts}


@pytest.mark.asyncio
async def test_get_prompt_renders_creation_draft(mcp_server: str):
    async with streamable_http_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.get_prompt(
                "contribution_create",
                {"title": "Intro to MCP", "type": "SPEAKING", "date": "2026-02-14"},
            )
            text = result.messages[0].content.text
            assert "Intro to MCP" in text
            assert "create_contribution" in text


@pytest.mark.asyncio
async def test_get_prompt_returns_structured_error(mcp_server: str):
    async with streamable_http_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.get_prompt(
                "contributions_stats",
                {"username": "alice", "group_by": "quarter"},
            )
            text = result.messages[0].content.text
            assert text.startswith("[ERROR] contributions_stats")
            assert '"group_by"' in text
            assert '"month"' in text


@pytest.mark.asyncio
async def test_get_prompt_reports_missing_required_argument(mcp_server: str):
    async with streamable_http_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.get_prompt(
                "contributions_stats", {"group_by": "type"}
            )
            text = result.messages[0].content.text
            assert text.startswith("[ERROR] contributions_stats")
            assert '"username": "required"' in text


@pytest.mark.asyncio
async def test_completion_suggests_contribution_types(mcp_server: str):
    async with streamable_http_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.complete(
                ref=PromptReference(name="contribution_create"),
                argument={"name": "type", "value": "blog"},
            )
            assert result.completion.values == ["BLOGPOST"]


@pytest.mark.asyncio
async def test_completion_suggests_stats_groupings(mcp_server: str):
    async with streamable_http_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.complete(
                ref=PromptReference(name="contributions_stats"),
                argument={"name": "group_by", "value": ""},
            )
            assert result.completion.values == ["month", "type", "year"]
