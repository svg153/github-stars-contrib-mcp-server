"""Unit tests for search_contributions tool."""

import pytest

from github_stars_contrib_mcp.tools import search_contributions as tool


class TestSearchContributions:
    @pytest.mark.asyncio
    async def test_requires_username(self):
        res = await tool.search_contributions_impl({})
        assert res["success"] is False
        assert "username" in res["error"]

    @pytest.mark.asyncio
    async def test_filters_by_type_and_title_and_date(self, monkeypatch):
        class FakePort:
            async def get_stars(self, username: str):
                return {
                    "publicProfile": {
                        "username": username,
                        "contributions": [
                            {
                                "type": "BLOGPOST",
                                "title": "Intro to MCP",
                                "date": "2025-01-10T10:00:00Z",
                            },
                            {
                                "type": "SPEAKING",
                                "title": "Deep dive",
                                "date": "2025-02-15T10:00:00Z",
                            },
                            {
                                "type": "BLOGPOST",
                                "title": "Advanced MCP",
                                "date": "2025-03-20T10:00:00Z",
                            },
                        ],
                    }
                }

        # Patch DI to use our FakePort
        monkeypatch.setattr(tool, "get_stars_api", FakePort)

        res = await tool.search_contributions_impl(
            {
                "username": "u",
                "type": "BLOGPOST",
                "title_contains": "MCP",
                "date_from": "2025-01-01",
                "date_to": "2025-02-28",
            }
        )
        assert res["success"] is True
        data = res["data"]
        assert len(data) == 1
        assert data[0]["title"] == "Intro to MCP"

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, monkeypatch):
        class FakePort:
            async def get_stars(self, username: str):
                return {
                    "publicProfile": {
                        "username": username,
                        "contributions": [
                            {
                                "type": "BLOGPOST",
                                "title": "t",
                                "date": "2025-01-01T00:00:00Z",
                            }
                        ],
                    }
                }

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.search_contributions_impl(
            {
                "username": "u",
                "date_from": "not-a-date",
            }
        )
        assert res["success"] is False
        assert "Invalid date format" in res["error"]
