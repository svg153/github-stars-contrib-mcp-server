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
        # WEBSITE is aliased to OTHER in live API enum
        assert res["data"] == {
            "updateLink": {
                "id": "l1",
                "link": "https://updated.com",
                "platform": "OTHER",
            }
        }

    @pytest.mark.asyncio
    async def test_update_link_invalid_url(self):
        data = {"link": "not-a-url"}
        res = await tool.update_link_impl("l1", data)
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_link_invalid_platform(self):
        data = {"platform": "INVALID"}
        res = await tool.update_link_impl("l1", data)
        assert res["success"] is False
        assert "platform" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_link_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def update_link(
                self, link_id: str, link: str | None, platform: str | None
            ):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", FailingPort)
        data = {"link": "https://example.com"}
        res = await tool.update_link_impl("l1", data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
    async def test_update_link_partial_update(self, mock_shared_client, monkeypatch):
        class FakePort2:
            async def update_link(
                self, link_id: str, link: str | None, platform: str | None
            ):
                return {"updateLink": {"id": link_id}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort2)

        data = {"platform": "GITHUB"}
        res = await tool.update_link_impl("l1", data)
        assert res["success"] is True

    @pytest.mark.asyncio
    async def test_update_link_alias_platform(self, monkeypatch):
        calls = {}

        class FakePort:
            async def update_link(
                self, link_id: str, link: str | None, platform: str | None
            ):
                calls["platform"] = platform
                return {"updateLink": {"id": link_id, "platform": platform}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.update_link_impl("l1", {"platform": "GITHUB"})
        assert res["success"] is True
        assert calls["platform"] == "GITHUB"
        # WEBSITE alias
        res2 = await tool.update_link_impl("l2", {"platform": "WEBSITE"})
        assert res2["success"] is True
        assert calls["platform"] == "OTHER"

    @pytest.mark.asyncio
    async def test_update_link_logger_initialization(self):
        """Test that logger is properly initialized."""
        from github_stars_contrib_mcp.tools.update_link import logger

        # Ensure logger is initialized (this covers the logger definition)
        assert logger is not None
        assert hasattr(logger, "info")  # Basic logger check
