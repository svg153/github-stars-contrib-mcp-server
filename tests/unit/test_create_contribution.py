"""Unit tests for create_contribution tool (DI path)."""

from datetime import datetime

import pytest

from github_stars_contrib_mcp.tools import create_contribution as tool


class TestCreateContribution:
    @pytest.mark.asyncio
    async def test_create_contribution_valid(self, monkeypatch):
        calls = {}

        class FakePort:
            async def create_contribution(self, **kwargs):
                calls.update(kwargs)
                return {"createContribution": {"id": "1", "type": "BLOGPOST"}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        data = {
            "title": "Test",
            "url": "https://example.com/path?source=stars",
            "description": None,
            "type": "BLOGPOST",
            "date": "2024-01-01T00:00:00Z",
        }

        res = await tool.create_contribution_impl(data)
        assert res["success"] is True
        assert res["contribution"]["id"] == "1"
        assert calls["url"] == "https://example.com/path?source=stars"
        assert calls["description"] == ""
        assert calls["date"] == "2024-01-01T00:00:00+00:00"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "date",
        [
            "2024-01-01T00:00:00Z",
            "2024-12-31T23:59:59+00:00",
            "2024-06-01T12:30:45+02:00",
        ],
    )
    async def test_create_contribution_accepts_timezone_boundaries(self, monkeypatch, date):
        class FakePort:
            async def create_contribution(self, **kwargs):
                return {"createContribution": {"id": "1"}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.create_contribution_impl(
            {
                "title": "Test",
                "url": "https://example.com/no-trailing-slash",
                "type": "BLOGPOST",
                "date": date,
            }
        )
        assert res["success"] is True

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
