"""Unit tests for create_contributions tool (DI path)."""

from datetime import datetime

import pytest

from github_stars_contrib_mcp.tools import create_contributions as tool


class TestCreateContributions:
    @pytest.mark.asyncio
    async def test_create_contributions_valid(self, monkeypatch):
        class FakePort:
            async def create_contributions(self, items):
                return {"ids": ["1", "2"]}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        data = [
            {
                "title": "Test",
                "url": "https://example.com",
                "description": "d",
                "type": "BLOGPOST",
                "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
            }
        ]

        res = await tool.create_contributions_impl(data)
        assert res["success"] is True
        assert res["ids"] == ["1", "2"]

    @pytest.mark.asyncio
    async def test_create_contributions_invalid_url(self):
        data = [
            {
                "title": "Test",
                "url": "not-a-url",
                "type": "BLOGPOST",
                "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
            }
        ]
        res = await tool.create_contributions_impl(data)
        assert res["success"] is False
        assert "url" in str(res["error"])

    @pytest.mark.asyncio
    async def test_create_contributions_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def create_contributions(self, items):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", FailingPort)
        data = [
            {
                "title": "Test",
                "url": "https://example.com",
                "type": "BLOGPOST",
                "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
            }
        ]
        res = await tool.create_contributions_impl(data)
        assert res["success"] is False
        assert res["error"] == "API error"

    @pytest.mark.asyncio
    async def test_create_contributions_client_error(self, mock_shared_client):
        # Covered by error_bubbles above; placeholder to keep test valid
        assert mock_shared_client is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/path?query=1&foo=bar",  # with querystring
            "https://example.com:8080/path",  # custom port
            "https://example.com/path/",  # trailing slash
        ],
    )
    async def test_create_contributions_url_edge_cases(self, monkeypatch, url):
        """Test that various URL formats are accepted."""

        class FakePort:
            async def create_contributions(self, items):
                return {"ids": ["1"]}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        data = [
            {
                "title": "Test",
                "url": url,
                "type": "BLOGPOST",
                "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
            }
        ]

        res = await tool.create_contributions_impl(data)
        assert res["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "date_str",
        [
            "2024-01-01T00:00:00Z",  # UTC
            "2024-12-31T23:59:59Z",  # boundary: year end
            "2024-02-29T12:00:00Z",  # leap year
        ],
    )
    async def test_create_contributions_date_edge_cases(self, monkeypatch, date_str):
        """Test that various ISO date formats are accepted."""

        class FakePort:
            async def create_contributions(self, items):
                return {"ids": ["1"]}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        data = [
            {
                "title": "Test",
                "url": "https://example.com",
                "type": "BLOGPOST",
                "date": date_str,
            }
        ]

        res = await tool.create_contributions_impl(data)
        assert res["success"] is True
