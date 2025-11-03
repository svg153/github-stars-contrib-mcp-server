"""Integration tests for MCP tool profile end-to-end."""

from __future__ import annotations

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.tools.update_profile import update_profile_impl

from .test_integration_utils import (
    require_token_or_skip,
    should_skip_mutations,
    get_test_client,
)


@pytest.mark.asyncio
@pytest.mark.tools
async def test_tools_profile_e2e():
    require_token_or_skip()
    if should_skip_mutations():
        pytest.skip("Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run")

    client = get_test_client()
    shared.stars_client = client
    try:
        # Read current user data via client; if loggedUser is null, skip safely
        cur = await client.get_user_data()
        if not cur.get("ok") or not (cur.get("data") or {}).get("loggedUser"):
            pytest.skip("Token not valid for reading user data or loggedUser is null; skipping tool flow test")

        nominee = (cur.get("data") or {}).get("loggedUser", {}).get("nominee", {})
        original_bio = nominee.get("bio") if nominee else None

        bio_test = f"E2E Tools Bio"
        up_bio = await update_profile_impl({"bio": bio_test})
        assert up_bio["success"] is True

        # Verify and revert
        back = await client.get_user_data()
        back_bio = (back.get("data") or {}).get("loggedUser", {}).get("nominee", {}).get("bio")
        assert back_bio == bio_test

        revert_data = {"bio": original_bio or ""}
        revert_res = await update_profile_impl(revert_data)
        assert revert_res["success"] is True
    finally:
        shared.stars_client = None
