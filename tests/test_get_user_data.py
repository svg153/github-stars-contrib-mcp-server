import pytest
from unittest.mock import AsyncMock

from github_stars_contrib_mcp.tools.get_user_data import get_user_data_impl
from github_stars_contrib_mcp import shared


@pytest.mark.asyncio
async def test_get_user_data_success():
    mock_client = AsyncMock()
    mock_client.get_user_data.return_value = {"ok": True, "data": {"loggedUser": {"id": "u1"}}}
    shared.stars_client = mock_client

    res = await get_user_data_impl()
    assert res["success"] is True
    assert res["data"]["loggedUser"]["id"] == "u1"


@pytest.mark.asyncio
async def test_get_user_data_not_initialized():
    shared.stars_client = None
    res = await get_user_data_impl()
    assert res["success"] is False
    assert res["data"] is None
