"""Unit tests for get_stars tool."""

import pytest
from unittest.mock import patch

from github_stars_contrib_mcp.tools.get_stars import get_stars_impl
from github_stars_contrib_mcp import shared


class TestGetStars:
    @pytest.mark.asyncio
    async def test_get_stars_success(self, mock_shared_client):
        mock_shared_client.get_stars.return_value = {"ok": True, "data": {"publicProfile": {"username": "u"}}}

        res = await get_stars_impl("u")
        assert res["success"] is True
        assert res["data"]["publicProfile"]["username"] == "u"

    @pytest.mark.asyncio
    async def test_get_stars_not_initialized(self):
        with patch.object(shared, 'stars_client', None):
            res = await get_stars_impl("u")
            assert res["success"] is False
            assert res["data"] is None

    @pytest.mark.asyncio
    async def test_get_stars_client_error(self, mock_shared_client):
        mock_shared_client.get_stars.return_value = {"ok": False, "error": "API error", "data": None}

        res = await get_stars_impl("u")
        assert res["success"] is False
        assert res["error"] == "API error"