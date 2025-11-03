"""Unit tests for create_link tool (DI path)."""

import pytest

from github_stars_contrib_mcp.tools import create_link as tool


class TestCreateLink:
    @pytest.mark.asyncio
    async def test_create_link_valid(self, monkeypatch):
        class FakePort:
            async def create_link(self, link: str, platform: str):
                return {"createLink": {"id": "123", "link": link, "platform": platform, "__typename": "Link"}}

        monkeypatch.setattr(tool, "get_stars_api", lambda: FakePort())
        res = await tool.create_link_impl("https://google.com/", "OTHER")
        assert res["success"] is True
        assert res["data"] == {"createLink": {"id": "123", "link": "https://google.com/", "platform": "OTHER", "__typename": "Link"}}

    @pytest.mark.asyncio
    async def test_create_link_invalid_url(self):
        res = await tool.create_link_impl("not-a-url", "OTHER")
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_create_link_invalid_platform(self):
        res = await tool.create_link_impl("https://google.com/", "INVALID")
        assert res["success"] is False
        assert "platform" in str(res["error"])

    @pytest.mark.asyncio
    async def test_create_link_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def create_link(self, link: str, platform: str):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", lambda: FailingPort())
        res = await tool.create_link_impl("https://google.com/", "OTHER")
        assert res["success"] is False
        assert res["error"] == "API error"