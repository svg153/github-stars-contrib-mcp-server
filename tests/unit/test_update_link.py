"""Unit tests for update_link tool."""

from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp.tools.update_link import update_link_impl
from github_stars_contrib_mcp import shared


class TestUpdateLink:
    @pytest.mark.asyncio
    async def test_update_link_success(self, mock_shared_client):
        mock_shared_client.update_link.return_value = {
            "ok": True,
            "data": {"updateLink": {"id": "l1", "link": "https://updated.com", "platform": "WEBSITE"}}
        }

        data = {"link": "https://updated.com", "platform": "WEBSITE"}
        res = await update_link_impl("l1", data)
        assert res["success"] is True
        assert res["data"] == {"updateLink": {"id": "l1", "link": "https://updated.com", "platform": "WEBSITE"}}

    @pytest.mark.asyncio
    async def test_update_link_invalid_url(self):
        data = {"link": "not-a-url"}
        res = await update_link_impl("l1", data)
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_link_invalid_platform(self):
        data = {"platform": "INVALID"}
        res = await update_link_impl("l1", data)
        assert res["success"] is False
        assert "platform" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_link_no_client(self):
        with patch.object(shared, 'stars_client', None):
            data = {"link": "https://example.com"}
            res = await update_link_impl("l1", data)
            assert res["success"] is False
            assert "not initialized" in res["error"]

    @pytest.mark.asyncio
    async def test_update_link_client_error(self, mock_shared_client):
        mock_shared_client.update_link.return_value = {"ok": False, "error": "API error", "data": None}

        data = {"link": "https://example.com"}
        res = await update_link_impl("l1", data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
    async def test_update_link_partial_update(self, mock_shared_client):
        mock_shared_client.update_link.return_value = {
            "ok": True,
            "data": {"updateLink": {"id": "l1"}}
        }

        data = {"platform": "GITHUB"}
        res = await update_link_impl("l1", data)
        assert res["success"] is True

    @pytest.mark.asyncio
    async def test_update_link_logger_initialization(self):
        """Test that logger is properly initialized."""
        from github_stars_contrib_mcp.tools.update_link import logger

        # Ensure logger is initialized (this covers the logger definition)
        assert logger is not None
        assert hasattr(logger, 'info')  # Basic logger check