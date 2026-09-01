"""Tests for REST-based Stars token validation."""

from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.utils.models import APIResult


@pytest.mark.asyncio
async def test_initialize_stars_client_validates_via_rest():
    with (
        patch("github_stars_contrib_mcp.shared.settings") as settings,
        patch("github_stars_contrib_mcp.shared.StarsClient") as client_cls,
    ):
        settings.stars_api_token = "token"
        settings.stars_api_url = "https://api-stars.github.com/"
        settings.stars_contributions_api_url = (
            "https://stars.github.com/api/contributions"
        )
        settings.dangerously_omit_auth = False
        fake = AsyncMock()
        fake.validate_token.return_value = APIResult(True, {"data": []})
        client_cls.return_value = fake

        await shared.initialize_stars_client()

        fake.validate_token.assert_awaited_once_with()
        client_cls.assert_called_once_with(
            api_url="https://api-stars.github.com/",
            contributions_api_url="https://stars.github.com/api/contributions",
            token="token",
        )


@pytest.mark.asyncio
async def test_initialize_stars_client_rejects_invalid_rest_token():
    with (
        patch("github_stars_contrib_mcp.shared.settings") as settings,
        patch("github_stars_contrib_mcp.shared.StarsClient") as client_cls,
    ):
        settings.stars_api_token = "bad"
        settings.stars_api_url = "https://api-stars.github.com/"
        settings.stars_contributions_api_url = (
            "https://stars.github.com/api/contributions"
        )
        settings.dangerously_omit_auth = False
        fake = AsyncMock()
        fake.validate_token.return_value = APIResult(False, None, "HTTP 401")
        client_cls.return_value = fake

        with pytest.raises(ValueError, match="Invalid STARS_API_TOKEN"):
            await shared.initialize_stars_client()
