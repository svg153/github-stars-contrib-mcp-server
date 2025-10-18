"""Unit tests for create_contribution tool."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp.tools.create_contribution import create_contribution_impl
from github_stars_contrib_mcp import shared


class TestCreateContribution:
    @pytest.mark.asyncio
    async def test_create_contribution_valid(self, mock_shared_client):
        # Mock client response
        mock_result = {"ok": True, "data": {"createContribution": {"id": "1", "type": "BLOGPOST"}}, "error": None}
        mock_shared_client.create_contribution.return_value = mock_result

        data = {
            "title": "Test",
            "url": "https://example.com",
            "description": "d",
            "type": "BLOGPOST",
            "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
        }

        res = await create_contribution_impl(data)
        assert res["success"] is True
        assert res["contribution"]["id"] == "1"

    @pytest.mark.asyncio
    async def test_create_contribution_invalid_url(self):
        data = {
            "title": "Test",
            "url": "not-a-url",
            "type": "BLOGPOST",
            "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
        }
        res = await create_contribution_impl(data)
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_create_contribution_no_client(self):
        with patch.object(shared, 'stars_client', None):
            data = {
                "title": "Test",
                "url": "https://example.com",
                "type": "BLOGPOST",
                "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
            }
            res = await create_contribution_impl(data)
            assert res["success"] is False
            assert "not initialized" in res["error"]