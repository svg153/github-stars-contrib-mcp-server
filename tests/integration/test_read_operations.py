"""Integration tests for read operations."""

import os

import pytest

from github_stars_contrib_mcp.tools.get_user_data import get_user_data_impl
from github_stars_contrib_mcp.tools.get_user import get_user_impl
from github_stars_contrib_mcp import shared
from .test_integration_utils import get_test_client


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_get_user_data():
    token = os.getenv("STARS_API_TOKEN")
    if not token:
        pytest.skip("STARS_API_TOKEN not set; skipping integration test")

    client = get_test_client()

    res = await client.get_user_data()
    assert res.get("ok") is True
    data = res.get("data") or {}
    assert "loggedUser" in data
    # If loggedUser exists and has data, validate shape
    if data.get("loggedUser"):
        assert "id" in data["loggedUser"]
        nominee = data["loggedUser"].get("nominee")
        if nominee and "contributions" in nominee:
            assert isinstance(nominee["contributions"], list)


@pytest.mark.asyncio
@pytest.mark.tools
async def test_integration_get_user_data_tool_flow():
    """Test the complete get_user_data tool flow with real API."""
    token = os.getenv("STARS_API_TOKEN")
    if not token:
        pytest.skip("STARS_API_TOKEN not set; skipping integration test")

    client = get_test_client()

    # First check if token is valid by calling client directly
    check_res = await client.get_user_data()
    if not check_res.get("ok") or not check_res.get("data", {}).get("loggedUser"):
        pytest.skip("Token not valid for reading user data or loggedUser is null; skipping tool flow test")

    # Initialize shared client with real API
    shared.stars_client = client

    try:
        res = await get_user_data_impl()
        assert res["success"] is True
        assert "data" in res
        data = res["data"]
        assert "loggedUser" in data
        if data.get("loggedUser"):
            assert "id" in data["loggedUser"]
    finally:
        # Clean up
        shared.stars_client = None


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_get_user():
    token = os.getenv("STARS_API_TOKEN")
    if not token:
        pytest.skip("STARS_API_TOKEN not set; skipping integration test")

    client = get_test_client()

    res = await client.get_user()
    assert res.get("ok") is True
    data = res.get("data") or {}
    assert "loggedUser" in data
    # If loggedUser exists and has data, validate shape
    if data.get("loggedUser"):
        assert "id" in data["loggedUser"]
        nominee = data["loggedUser"].get("nominee")
        if nominee and "status" in nominee:
            assert isinstance(nominee["status"], str)
        nominations = data["loggedUser"].get("nominations")
        if nominations:
            assert isinstance(nominations, list)


@pytest.mark.asyncio
@pytest.mark.tools
async def test_integration_get_user_tool_flow():
    """Test the complete get_user tool flow with real API."""
    token = os.getenv("STARS_API_TOKEN")
    if not token:
        pytest.skip("STARS_API_TOKEN not set; skipping integration test")

    client = get_test_client()

    # First check if token is valid by calling client directly
    check_res = await client.get_user()
    if not check_res.get("ok") or not check_res.get("data", {}).get("loggedUser"):
        pytest.skip("Token not valid for reading user data or loggedUser is null; skipping tool flow test")

    # Initialize shared client with real API
    shared.stars_client = client

    try:
        res = await get_user_impl()
        assert res["success"] is True
        assert "data" in res
        data = res["data"]
        assert "loggedUser" in data
        if data.get("loggedUser"):
            assert "id" in data["loggedUser"]
    finally:
        # Clean up
        shared.stars_client = None