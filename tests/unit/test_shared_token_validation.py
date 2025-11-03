"""Unit tests for shared.initialize_stars_client token validation flows."""

from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.utils.models import APIResult


@pytest.mark.asyncio
async def test_initialize_stars_client_invalid_token_raises():
    # Simulate having a token but validation failing when fetching user data
    with patch("github_stars_contrib_mcp.shared.settings") as mock_settings, \
         patch("github_stars_contrib_mcp.shared.StarsClient") as mock_client_cls:
        mock_settings.stars_api_token = "bad-token"
        mock_settings.dangerously_omit_auth = False

        mock_client = AsyncMock()
        mock_client.get_user_data.return_value = APIResult(ok=False, error="bad", data=None)
        mock_client_cls.return_value = mock_client

        with pytest.raises(ValueError):
            await shared.initialize_stars_client()


@pytest.mark.asyncio
async def test_initialize_stars_client_no_token_but_omitted():
    # No token and omit auth -> should warn and leave stars_client as None
    with patch("github_stars_contrib_mcp.shared.settings") as mock_settings:
        mock_settings.stars_api_token = None
        mock_settings.dangerously_omit_auth = True
        await shared.initialize_stars_client()
        assert shared.stars_client is None
