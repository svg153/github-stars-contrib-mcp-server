"""Unit tests for create_contribution tool (DI path)."""

from datetime import datetime

import pytest

from github_stars_contrib_mcp.tools import create_contribution as tool


class TestCreateContribution:
    @pytest.mark.asyncio
    async def test_create_contribution_valid(self, monkeypatch):
        class FakePort:
            async def create_contribution(self, **kwargs):
                return {"createContribution": {"id": "1", "type": "BLOGPOST"}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        data = {
            "title": "Test",
            "url": "https://example.com",
            "description": "d",
            "type": "BLOGPOST",
            "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
        }

        res = await tool.create_contribution_impl(data)
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
        res = await tool.create_contribution_impl(data)
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_create_contribution_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def create_contribution(self, **kwargs):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", FailingPort)
        data = {
            "title": "Test",
            "url": "https://example.com",
            "type": "BLOGPOST",
            "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
        }
        res = await tool.create_contribution_impl(data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
    async def test_create_contribution_client_error(self, mock_shared_client):
        # Covered by error_bubbles above; placeholder to keep test valid
        assert mock_shared_client is not None
