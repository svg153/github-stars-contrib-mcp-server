"""Unit tests for update_profile tool (DI path)."""

import pytest

from github_stars_contrib_mcp.tools import update_profile as tool


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_profile_success(self, monkeypatch):
        class FakePort:
            async def update_profile(self, data: dict):
                return {"updateProfile": {"id": "user1"}}

        monkeypatch.setattr(tool, "get_stars_api", lambda: FakePort())

        data = {"name": "John Doe", "bio": "Updated bio"}
        res = await tool.update_profile_impl(data)
        assert res["success"] is True
        assert res["data"] == {"updateProfile": {"id": "user1"}}

    @pytest.mark.asyncio
    async def test_update_profile_invalid_birthdate(self):
        data = {"birthdate": "invalid-date"}
        res = await tool.update_profile_impl(data)
        assert res["success"] is False
        assert "birthdate" in str(res["error"])

    @pytest.mark.asyncio
    async def test_update_profile_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def update_profile(self, data: dict):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", lambda: FailingPort())
        data = {"name": "John Doe"}
        res = await tool.update_profile_impl(data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
        # Covered by error_bubbles above

    @pytest.mark.asyncio
    async def test_update_profile_partial_update(self, mock_shared_client, monkeypatch):
        class FakePort2:
            async def update_profile(self, data: dict):
                return {"updateProfile": {"id": "user1"}}

        monkeypatch.setattr(tool, "get_stars_api", lambda: FakePort2())

        data = {"jobTitle": "Engineer"}
        res = await tool.update_profile_impl(data)
        assert res["success"] is True

    @pytest.mark.asyncio
    async def test_update_profile_logger_initialization(self):
        """Test that logger is properly initialized."""
        from github_stars_contrib_mcp.tools.update_profile import logger

        # Ensure logger is initialized (this covers the logger definition)
        assert logger is not None
        assert hasattr(logger, 'info')  # Basic logger check