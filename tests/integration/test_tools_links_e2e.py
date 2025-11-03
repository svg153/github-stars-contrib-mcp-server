"""Integration tests for MCP tool links end-to-end."""

from __future__ import annotations

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.tools.create_link import create_link_impl
from github_stars_contrib_mcp.tools.delete_link import delete_link_impl
from github_stars_contrib_mcp.tools.update_link import update_link_impl

from .test_integration_utils import (
    generate_unique_url,
    get_test_client,
    require_token_or_skip,
    should_skip_mutations,
)


@pytest.mark.asyncio
@pytest.mark.tools
async def test_tools_links_e2e():
    require_token_or_skip()
    if should_skip_mutations():
        pytest.skip(
            "Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run"
        )

    client = get_test_client()
    shared.stars_client = client
    try:
        url = generate_unique_url("github-stars-mcp-tools-link")

        # Create (use OTHER which is accepted by API)
        create_res = await create_link_impl(link=url, platform="OTHER")
        assert create_res["success"] is True
        link_id = (create_res.get("data") or {}).get("createLink", {}).get("id")
        assert link_id

        # Update (platform is non-null in response; pass it to ensure it remains set)
        upd_res = await update_link_impl(
            link_id=link_id, data={"link": url + "/updated", "platform": "OTHER"}
        )
        assert upd_res["success"] is True

        # Delete
        del_res = await delete_link_impl(link_id=link_id)
        assert del_res["success"] is True
    finally:
        shared.stars_client = None
