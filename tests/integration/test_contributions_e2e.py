"""Live integration tests for the current Contributions REST API."""

import pytest

from .test_integration_utils import (
    get_current_iso_datetime,
    get_test_client,
    require_token_or_skip,
    skip_if_no_mutations,
)


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_list_contributions_e2e():
    require_token_or_skip()
    result = await get_test_client().list_contributions(page=1)
    assert result.ok is True
    assert isinstance(result.data, dict)
    assert isinstance(result.data.get("data", []), list)


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_upsert_contribution_e2e():
    """Use one stable client ID so repeated test runs do not create endless rows."""
    skip_if_no_mutations()
    client = get_test_client()
    payload = {
        "title": "github-stars-contrib-mcp e2e",
        "url": "https://github.com/svg153/github-stars-contrib-mcp-server",
        "description": "Stable automated REST upsert test record",
        "type": "OPEN_SOURCE_PROJECT",
        "date": get_current_iso_datetime(),
    }

    result = await client.upsert_contribution("github-stars-contrib-mcp:e2e", payload)

    assert result.ok is True
    assert "upsertContribution" in (result.data or {})
