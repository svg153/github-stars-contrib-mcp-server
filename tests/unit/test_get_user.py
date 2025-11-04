"""Unit tests for get_user tool (DI path)."""

import pytest

from github_stars_contrib_mcp.tools import get_user as tool


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self, monkeypatch):
        class FakePort:
            async def get_user(self):
                return {"loggedUser": {"id": "u1"}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.get_user_impl()
        assert res["success"] is True
        assert res["data"]["loggedUser"]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_get_user_error_bubbles(self, monkeypatch):
        class FailingPort:
            async def get_user(self):
                raise RuntimeError("API error")

        monkeypatch.setattr(tool, "get_stars_api", FailingPort)
        res = await tool.get_user_impl()
        assert res["success"] is False
        assert res["error"] == "API error"
        assert res["data"] is None

    @pytest.mark.asyncio
    async def test_get_user_includes_nominations(self, monkeypatch):
        class FakePort:
            async def get_user(self):
                return {
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
                }

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.get_user_impl()
        assert res["success"] is True
        noms = res["data"]["loggedUser"]["nominations"]
        assert isinstance(noms, list) and len(noms) == 2
        assert {n["id"] for n in noms} == {"n1", "n2"}

    @pytest.mark.asyncio
    async def test_get_user_no_nominee_ok(self, monkeypatch):
        class FakePort:
            async def get_user(self):
                return {"loggedUser": {"id": "u1", "nominee": {"status": "PENDING"}}}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.get_user_impl()
        assert res["success"] is True
        assert res["data"]["loggedUser"]["nominee"]["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_get_user_logged_user_null(self, monkeypatch):
        class FakePort:
            async def get_user(self):
                return {"loggedUser": None}

        monkeypatch.setattr(tool, "get_stars_api", FakePort)
        res = await tool.get_user_impl()
        assert res["success"] is True
        assert res["data"] is None
