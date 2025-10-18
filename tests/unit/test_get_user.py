"""Unit tests for get_user tool."""

import pytest
from unittest.mock import AsyncMock, patch

from github_stars_contrib_mcp.tools.get_user import get_user_impl
from github_stars_contrib_mcp import shared


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self, mock_shared_client):
        mock_shared_client.get_user.return_value = {"ok": True, "data": {"loggedUser": {"id": "u1"}}}

        res = await get_user_impl()
        assert res["success"] is True
        assert res["data"]["loggedUser"]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_get_user_not_initialized(self):
        with patch.object(shared, 'stars_client', None):
            res = await get_user_impl()
            assert res["success"] is False
            assert res["data"] is None

    @pytest.mark.asyncio
    async def test_get_user_includes_nominations(self, mock_shared_client):
        mock_shared_client.get_user.return_value = {
            "ok": True,
            "data": {
                "loggedUser": {
                    "id": "u1",
                    "nominations": [
                        {
                            "id": "n1",
                            "nominee": {
                                "id": "nu1",
                                "username": "user1",
                                "name": "User One",
                            },
                            "content": "Great work!",
                        },
                        {
                            "id": "n2",
                            "nominee": {
                                "id": "nu2",
                                "username": "user2",
                                "name": "User Two",
                            },
                            "content": "Awesome contribution!",
                        },
                    ],
                }
            },
        }

        res = await get_user_impl()
        assert res["success"] is True
        noms = res["data"]["loggedUser"]["nominations"]
        assert isinstance(noms, list) and len(noms) == 2
        assert {n["id"] for n in noms} == {"n1", "n2"}

    @pytest.mark.asyncio
    async def test_get_user_no_nominee_ok(self, mock_shared_client):
        mock_shared_client.get_user.return_value = {
            "ok": True,
            "data": {"loggedUser": {"id": "u1", "nominee": {"status": "PENDING"}}},
        }

        res = await get_user_impl()
        assert res["success"] is True
        assert res["data"]["loggedUser"]["nominee"]["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_get_user_client_error(self, mock_shared_client):
        mock_shared_client.get_user.return_value = {"ok": False, "error": "API error", "data": None}

        res = await get_user_impl()
        assert res["success"] is False
        assert res["error"] == "API error"
        assert res["data"] is None

    @pytest.mark.asyncio
    async def test_get_user_logged_user_null(self, mock_shared_client):
        mock_shared_client.get_user.return_value = {"ok": True, "data": {"loggedUser": None}}

        res = await get_user_impl()
        assert res["success"] is True
        assert res["data"] is None