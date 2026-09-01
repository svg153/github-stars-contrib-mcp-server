"""Live integration tests for MCP contribution tool implementations."""

import pytest

from github_stars_contrib_mcp.tools.list_contributions import list_contributions_impl
from github_stars_contrib_mcp.tools.update_contributions import (
    upsert_contribution_impl,
)

from .test_integration_utils import (
    get_current_iso_datetime,
    require_token_or_skip,
    should_skip_mutations,
)


@pytest.mark.asyncio
@pytest.mark.tools
async def test_list_contributions_tool_e2e():
    require_token_or_skip()
    result = await list_contributions_impl(page=1)
    assert result["success"] is True


@pytest.mark.asyncio
@pytest.mark.tools
async def test_upsert_contribution_tool_e2e():
    require_token_or_skip()
    if should_skip_mutations():
        pytest.skip(
            "Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run"
        )

    payload = {
        "title": "github-stars-contrib-mcp tool e2e",
        "url": "https://github.com/svg153/github-stars-contrib-mcp-server",
        "description": "Stable automated MCP tool upsert test record",
        "type": "OPEN_SOURCE_PROJECT",
        "date": get_current_iso_datetime(),
    }
    result = await upsert_contribution_impl(
        "github-stars-contrib-mcp:tool-e2e",
        payload,
    )
    assert result["success"] is True
