"""Unit tests for update_contributions tool."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp.tools.update_contributions import update_contribution_impl
from github_stars_contrib_mcp import shared


class TestUpdateContributions:
    @pytest.mark.asyncio
    async def test_update_contribution_success(self, mock_shared_client):
        mock_shared_client.update_contribution.return_value = {
            "ok": True,
            "data": {"updateContribution": {"id": "c1", "title": "Updated Title"}}
        }

        data = {"title": "Updated Title"}
        res = await update_contribution_impl("c1", data)
        assert res["success"] is True
        assert res["data"] == {"updateContribution": {"id": "c1", "title": "Updated Title"}}

    @pytest.mark.asyncio
    async def test_update_contribution_invalid_url(self):
        data = {"url": "not-a-url"}
        res = await update_contribution_impl("c1", data)
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_contribution_invalid_date(self):
        data = {"date": "not-a-date"}
        res = await update_contribution_impl("c1", data)
        assert res["success"] is False
        assert "date" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_contribution_no_client(self):
        with patch.object(shared, 'stars_client', None):
            data = {"title": "Test"}
            res = await update_contribution_impl("c1", data)
            assert res["success"] is False
            assert "not initialized" in res["error"]

    @pytest.mark.asyncio
    async def test_update_contribution_client_error(self, mock_shared_client):
        mock_shared_client.update_contribution.return_value = {"ok": False, "error": "API error", "data": None}

        data = {"title": "Test"}
        res = await update_contribution_impl("c1", data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
    async def test_update_contribution_full_update(self, mock_shared_client):
        mock_shared_client.update_contribution.return_value = {
            "ok": True,
            "data": {"updateContribution": {"id": "c1"}}
        }

        data = {
            "title": "New Title",
            "url": "https://example.com",
            "description": "New desc",
            "type": "BLOGPOST",
            "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
        }
        res = await update_contribution_impl("c1", data)
        assert res["success"] is True

    @pytest.mark.asyncio
    async def test_update_contribution_logger_initialization(self):
        """Test that logger is properly initialized."""
        from github_stars_contrib_mcp.tools.update_contributions import logger

        # Ensure logger is initialized (this covers the logger definition)
        assert logger is not None
        assert hasattr(logger, 'info')  # Basic logger check