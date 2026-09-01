"""No-token startup behavior."""

from unittest.mock import patch

import pytest

from github_stars_contrib_mcp import shared


@pytest.mark.asyncio
async def test_no_token_requires_explicit_unsafe_opt_out():
    with patch("github_stars_contrib_mcp.shared.settings") as settings:
        settings.stars_api_token = None
        settings.dangerously_omit_auth = False
        with pytest.raises(ValueError, match="STARS_API_TOKEN"):
            await shared.initialize_stars_client()


@pytest.mark.asyncio
async def test_no_token_allowed_only_when_explicitly_configured():
    with patch("github_stars_contrib_mcp.shared.settings") as settings:
        settings.stars_api_token = None
        settings.dangerously_omit_auth = True
        await shared.initialize_stars_client()
        assert shared.stars_client is None
