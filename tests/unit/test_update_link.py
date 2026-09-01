"""Unit tests for update_link tool (DI path)."""

import pytest

from github_stars_contrib_mcp.tools import update_link as tool


class TestUpdateLink:
    @pytest.mark.asyncio
    async def test_update_link_success(self, monkeypatch):
        class FakePort:
            async def update_link(
                self, link_id: str, link: str | None, platform: str | None
            ):
                return {
                    "updateLink": {"id": link_id, "link": link, "platform": platform}
                }

        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        data = {"link": "https://updated.com", "platform": "WEBSITE"}
        res = await tool.update_link_impl("l1", data)
        assert res["success"] is True
        assert res["error"] is None
        assert res["data"] == {
            "updateLink": {
                "id": "l1",
                "link": "https://updated.com",
                "platform": "OTHER",
            }
        }

    @pytest.mark.asyncio
    async def test_update_link_invalid_url(self):
        res = await tool.update_link_impl("l1", {"link": "not-a-url"})
        assert res["success"] is False
        assert res["data"] is None
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_link_invalid_platform(self):
        res = await tool.update_link_impl("l1", {"platform": "INVALID"})
        assert res["success"] is False
        assert res["data"] is None
        assert "Allowed:" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_link_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def update_link(
                self, link_id: str, link: str | None, platform: str | None
            ):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", FailingPort)
        res = await tool.update_link_impl("l1", {"link": "https://example.com"})
        assert res == {"success": False, "data": None, "error": "API error"}

    @pytest.mark.asyncio
    async def test_update_link_aliases_are_consistent(self, monkeypatch):
        calls = []

        class FakePort:
            async def update_link(
                self, link_id: str, link: str | None, platform: str | None
            ):
                calls.append(platform)
                return {"updateLink": {"id": link_id, "platform": platform}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        github = await tool.update_link_impl("l1", {"platform": "GITHUB"})
        website = await tool.update_link_impl("l2", {"platform": "WEBSITE"})

        assert github["success"] is True
        assert website["success"] is True
        assert calls == ["README", "OTHER"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("platform", ["LINKEDIN", "OTHER", "DEV_TO"])
    async def test_update_link_accepts_live_platform_values(self, monkeypatch, platform):
        calls = {}

        class FakePort:
            async def update_link(
                self, link_id: str, link: str | None, platform: str | None
            ):
                calls["platform"] = platform
                return {"updateLink": {"id": link_id}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.update_link_impl("l1", {"platform": platform})
        assert res["success"] is True
        assert calls["platform"] == platform
