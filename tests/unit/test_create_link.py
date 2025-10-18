"""Unit tests for create_link tool."""

from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp.tools.create_link import create_link_impl
from github_stars_contrib_mcp import shared


class TestCreateLink:
    @pytest.mark.asyncio
    async def test_create_link_valid(self, mock_shared_client):
        # Mock client response
        mock_result = {"ok": True, "data": {"createLink": {"id": "123", "link": "https://google.com/", "platform": "OTHER", "__typename": "Link"}}, "error": None}
        mock_shared_client.create_link.return_value = mock_result

        res = await create_link_impl("https://google.com/", "OTHER")
        assert res["success"] is True
        assert res["data"] == mock_result["data"]

    @pytest.mark.asyncio
    async def test_create_link_invalid_url(self):
        res = await create_link_impl("not-a-url", "OTHER")
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_create_link_invalid_platform(self):
        res = await create_link_impl("https://google.com/", "INVALID")
        assert res["success"] is False
        assert "platform" in str(res["error"])

    @pytest.mark.asyncio
    async def test_create_link_no_client(self):
        with patch.object(shared, 'stars_client', None):
            res = await create_link_impl("https://google.com/", "OTHER")
            assert res["success"] is False
            assert "not initialized" in res["error"]