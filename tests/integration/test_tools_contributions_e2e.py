"""Integration tests for MCP tool contributions end-to-end."""

from __future__ import annotations

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.tools.create_contributions import (
    create_contributions_impl,
)
from github_stars_contrib_mcp.tools.delete_contributions import delete_contribution_impl
from github_stars_contrib_mcp.tools.update_contributions import update_contribution_impl

from .test_integration_utils import (
    generate_unique_url,
    get_current_iso_datetime,
    get_test_client,
    require_token_or_skip,
    should_skip_mutations,
)


@pytest.mark.asyncio
@pytest.mark.tools
async def test_tools_contributions_e2e():
    require_token_or_skip()
    if should_skip_mutations():
        pytest.skip("Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run")

    client = get_test_client()
    shared.stars_client = client
    try:
        now_iso = get_current_iso_datetime()
        url = generate_unique_url("github-stars-mcp-tools-contrib")
        base_payload = {
            "title": "E2E Tools Contribution",
            "url": url,
            "description": "Automated tools e2e test; safe to ignore",
            "type": "BLOGPOST",
            "date": now_iso,
        }

        # Create
        create_res = await create_contributions_impl([base_payload])
        assert create_res["success"] is True
        contrib_id = (create_res.get("ids") or [None])[0]
        assert contrib_id

        # Update (API expects non-null description, etc.)
        upd_payload = {**base_payload, "title": "E2E Tools Contribution (updated)"}
        upd_res = await update_contribution_impl(contribution_id=contrib_id, data=upd_payload)
        assert upd_res["success"] is True

        # Delete
        del_res = await delete_contribution_impl(contrib_id)
        assert del_res["success"] is True
    finally:
        shared.stars_client = None
