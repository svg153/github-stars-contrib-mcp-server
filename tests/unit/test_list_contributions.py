"""Tests for the authenticated REST list tool."""

import pytest

from github_stars_contrib_mcp.tools import list_contributions as tool


@pytest.mark.asyncio
async def test_list_contributions_returns_page(monkeypatch):
    class FakePort:
        async def list_contributions(self, page: int):
            return {"data": [{"id": "one"}], "pagination": {"page": page}}

    monkeypatch.setattr(tool, "get_stars_api", FakePort)
    result = await tool.list_contributions_impl(3)
    assert result["success"] is True
    assert result["data"]["pagination"]["page"] == 3
