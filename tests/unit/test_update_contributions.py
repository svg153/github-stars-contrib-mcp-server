"""Tests for full-payload REST upsert semantics."""

# This import layout is already intentionally split into third-party and first-party
# sections; Ruff 0.16.5 reports a false-positive I001 for this single alias import.
# ruff: noqa: I001
import pytest

from github_stars_contrib_mcp.tools import update_contributions as tool


FULL = {
    "title": "Updated",
    "url": "https://example.com/post",
    "description": "Description",
    "type": "BLOGPOST",
    "date": "2026-08-25T00:00:00Z",
}


@pytest.mark.asyncio
async def test_upsert_requires_complete_payload():
    result = await tool.upsert_contribution_impl("stable-id", {"title": "Only title"})
    assert result["success"] is False


@pytest.mark.asyncio
async def test_upsert_sends_canonical_enum_value(monkeypatch):
    class FakePort:
        async def upsert_contribution(self, client_id: str, data: dict):
            assert client_id == "stable-id"
            assert data["type"] == "BLOGPOST"
            assert data["url"] == "https://example.com/post"
            return {"upsertContribution": {"id": "server-id"}}

    monkeypatch.setattr(tool, "get_stars_api", FakePort)
    result = await tool.upsert_contribution_impl("stable-id", FULL)
    assert result == {"success": True, "data": {"id": "server-id"}}


@pytest.mark.asyncio
async def test_upsert_surfaces_adapter_errors(monkeypatch):
    class FailingPort:
        async def upsert_contribution(self, client_id: str, data: dict):
            raise RuntimeError("API error")

    monkeypatch.setattr(tool, "get_stars_api", FailingPort)
    result = await tool.upsert_contribution_impl("stable-id", FULL)
    assert result == {"success": False, "error": "API error"}
