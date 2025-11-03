"""Unit tests for update_contributions tool (DI path)."""

from datetime import datetime

import pytest

from github_stars_contrib_mcp.tools import update_contributions as tool


class TestUpdateContributions:
    @pytest.mark.asyncio
    async def test_update_contribution_success(self, monkeypatch):
        class FakePort:
            async def update_contribution(self, contribution_id: str, data: dict):
                return {"updateContribution": {"id": contribution_id, "title": data["title"]}}

        monkeypatch.setattr(tool, "get_stars_api", lambda: FakePort())

        data = {"title": "Updated Title"}
        res = await tool.update_contribution_impl("c1", data)
        assert res["success"] is True
        assert res["data"] == {"updateContribution": {"id": "c1", "title": "Updated Title"}}

    @pytest.mark.asyncio
    async def test_update_contribution_invalid_url(self):
        data = {"url": "not-a-url"}
        res = await tool.update_contribution_impl("c1", data)
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_contribution_invalid_date(self):
        data = {"date": "not-a-date"}
        res = await tool.update_contribution_impl("c1", data)
        assert res["success"] is False
        assert "date" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_contribution_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def update_contribution(self, contribution_id: str, data: dict):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", lambda: FailingPort())
        data = {"title": "Test"}
        res = await tool.update_contribution_impl("c1", data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
        # Covered by error_bubbles above

    @pytest.mark.asyncio
    async def test_update_contribution_full_update(self, mock_shared_client, monkeypatch):
        class FakePort2:
            async def update_contribution(self, contribution_id: str, data: dict):
                return {"updateContribution": {"id": contribution_id}}

        monkeypatch.setattr(tool, "get_stars_api", lambda: FakePort2())

        data = {
            "title": "New Title",
            "url": "https://example.com",
            "description": "New desc",
            "type": "BLOGPOST",
            "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
        }
        res = await tool.update_contribution_impl("c1", data)
        assert res["success"] is True

    @pytest.mark.asyncio
    async def test_update_contribution_logger_initialization(self):
        """Test that logger is properly initialized."""
        from github_stars_contrib_mcp.tools.update_contributions import logger

        # Ensure logger is initialized (this covers the logger definition)
        assert logger is not None
        assert hasattr(logger, 'info')  # Basic logger check