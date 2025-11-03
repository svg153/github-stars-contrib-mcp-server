"""Integration tests for MCP tool read-only flows.

These tests wire `shared.stars_client` to a real StarsClient using env vars and
exercise the read-only tool implementation functions to avoid duplicating logic.
"""

from __future__ import annotations

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.tools.get_stars import get_stars_impl
from github_stars_contrib_mcp.tools.get_user import get_user_impl

from .test_integration_utils import get_test_client, require_token_or_skip


@pytest.mark.asyncio
@pytest.mark.tools
async def test_tools_read_only():
    require_token_or_skip()
    client = get_test_client()
    # Wire shared client for tools
    shared.stars_client = client
    try:
        # get_user_impl may return loggedUser null; still should be success
        res_user = await get_user_impl()
        assert res_user["success"] is True
        # get_stars_impl for a known username
        res_stars = await get_stars_impl("svg153")
        assert res_stars["success"] is True
        data = res_stars.get("data", {})
        assert "publicProfile" in data
        if data.get("publicProfile"):
            prof = data["publicProfile"]
            assert "contributions" in prof
    finally:
        shared.stars_client = None

