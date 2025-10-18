"""Unit tests for update_profile tool."""

from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp.tools.update_profile import update_profile_impl
from github_stars_contrib_mcp import shared


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_profile_success(self, mock_shared_client):
        mock_shared_client.update_profile.return_value = {
            "ok": True,
            "data": {"updateProfile": {"id": "user1"}}
        }

        data = {"name": "John Doe", "bio": "Updated bio"}
        res = await update_profile_impl(data)
        assert res["success"] is True
        assert res["data"] == {"updateProfile": {"id": "user1"}}

    @pytest.mark.asyncio
    async def test_update_profile_invalid_birthdate(self):
        data = {"birthdate": "invalid-date"}
        res = await update_profile_impl(data)
        assert res["success"] is False
        assert "birthdate" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_profile_no_client(self):
        with patch.object(shared, 'stars_client', None):
            data = {"name": "John Doe"}
            res = await update_profile_impl(data)
            assert res["success"] is False
            assert "not initialized" in res["error"]

    @pytest.mark.asyncio
    async def test_update_profile_client_error(self, mock_shared_client):
        mock_shared_client.update_profile.return_value = {"ok": False, "error": "API error", "data": None}

        data = {"name": "John Doe"}
        res = await update_profile_impl(data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
    async def test_update_profile_partial_update(self, mock_shared_client):
        mock_shared_client.update_profile.return_value = {
            "ok": True,
            "data": {"updateProfile": {"id": "user1"}}
        }

        data = {"jobTitle": "Engineer"}
        res = await update_profile_impl(data)
        assert res["success"] is True

    @pytest.mark.asyncio
    async def test_update_profile_logger_initialization(self):
        """Test that logger is properly initialized."""
        from github_stars_contrib_mcp.tools.update_profile import logger

        # Ensure logger is initialized (this covers the logger definition)
        assert logger is not None
        assert hasattr(logger, 'info')  # Basic logger check