"""Unit tests for get_user_data tool."""

from unittest.mock import patch

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.tools.get_user_data import get_user_data_impl


class TestGetUserData:
    @pytest.mark.asyncio
    async def test_get_user_data_success(self, mock_shared_client):
        mock_shared_client.get_user_data.return_value = {
            "ok": True,
            "data": {"loggedUser": {"id": "u1"}},
        }

        res = await get_user_data_impl()
        assert res["success"] is True
        assert res["data"]["loggedUser"]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_get_user_data_not_initialized(self):
        with patch.object(shared, "stars_client", None):
            res = await get_user_data_impl()
            assert res["success"] is False
            assert res["data"] is None

    @pytest.mark.asyncio
    async def test_get_user_data_includes_contributions(self, mock_shared_client):
        mock_shared_client.get_user_data.return_value = {
            "ok": True,
            "data": {
                "loggedUser": {
                    "id": "u1",
                    "nominee": {
                        "contributions": [
                            {
                                "id": "c1",
                                "type": "BLOGPOST",
                                "date": "2024-01-01T00:00:00Z",
                                "title": "Post",
                                "url": "https://example.com",
                                "description": "desc",
                            },
                            {
                                "id": "c2",
                                "type": "SPEAKING",
                                "date": "2024-02-01T00:00:00Z",
                                "title": "Talk",
                                "url": "https://talks.example.com",
                                "description": None,
                            },
                        ]
                    },
                }
            },
        }

        res = await get_user_data_impl()
        assert res["success"] is True
        contribs = res["data"]["loggedUser"]["nominee"]["contributions"]
        assert isinstance(contribs, list) and len(contribs) == 2
        assert {c["id"] for c in contribs} == {"c1", "c2"}

    @pytest.mark.asyncio
    async def test_get_user_data_no_nominee_ok(self, mock_shared_client):
        mock_shared_client.get_user_data.return_value = {
            "ok": True,
            "data": {"loggedUser": {"id": "u1", "nominee": None}},
        }

        res = await get_user_data_impl()
        assert res["success"] is True
        assert res["data"]["loggedUser"]["nominee"] is None

    @pytest.mark.asyncio
    async def test_get_user_data_client_error(self, mock_shared_client):
        mock_shared_client.get_user_data.return_value = {
            "ok": False,
            "error": "API error",
            "data": None,
        }

        res = await get_user_data_impl()
        assert res["success"] is False
        assert res["error"] == "API error"
        assert res["data"] is None

    @pytest.mark.asyncio
    async def test_get_user_data_logged_user_null(self, mock_shared_client):
        mock_shared_client.get_user_data.return_value = {
            "ok": True,
            "data": {"loggedUser": None},
        }

        res = await get_user_data_impl()
        assert res["success"] is True
        assert res["data"] is None
