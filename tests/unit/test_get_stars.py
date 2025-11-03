"""Unit tests for get_stars tool (DI path)."""

import pytest

from github_stars_contrib_mcp.tools import get_stars as tool


class TestGetStars:
    @pytest.mark.asyncio
    async def test_get_stars_success(self, monkeypatch):
        class FakePort:
            async def get_stars(self, username: str):
                return {"publicProfile": {"username": username}}

        monkeypatch.setattr(tool, "get_stars_api", lambda: FakePort())
        res = await tool.get_stars_impl("u")
        assert res["success"] is True
        assert res["data"]["publicProfile"]["username"] == "u"

    @pytest.mark.asyncio
    async def test_get_stars_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def get_stars(self, username: str):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", lambda: FailingPort())
        res = await tool.get_stars_impl("u")
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
    async def test_get_stars_validates_username_in_use_case(self, monkeypatch):
        class FakePort:
            async def get_stars(self, username: str):
                return {"publicProfile": {"username": username}}

        monkeypatch.setattr(tool, "get_stars_api", lambda: FakePort())
        res = await tool.get_stars_impl("")
        # GetStars use case will raise ValueError, which tool wraps as error
        assert res["success"] is False
        assert "username" in res["error"]
