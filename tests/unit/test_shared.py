"""Tests for shared Stars and discovery bootstrap."""

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
        settings.stars_auth_mode = "both"
        settings.stars_user_agent = "github-stars-contrib-mcp-server/0.3.1"
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
            auth_mode="both",
            user_agent="github-stars-contrib-mcp-server/0.3.1",
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
        settings.stars_auth_mode = "both"
        settings.stars_user_agent = "github-stars-contrib-mcp-server/0.3.1"
        settings.dangerously_omit_auth = False
        fake = AsyncMock()
        fake.validate_token.return_value = APIResult(False, None, "HTTP 401")
        client_cls.return_value = fake

        with pytest.raises(ValueError, match="Invalid STARS_API_TOKEN"):
            await shared.initialize_stars_client()


def test_initialize_discovery_repository_is_lazy_and_cached():
    original = shared.discovery_repository
    shared.discovery_repository = None
    try:
        with (
            patch("github_stars_contrib_mcp.shared.settings") as settings,
            patch(
                "github_stars_contrib_mcp.shared.SQLiteDiscoveryRepository"
            ) as repository_cls,
        ):
            settings.discovery_db_path = "/tmp/stars-discovery.db"
            repository = object()
            repository_cls.return_value = repository

            first = shared.initialize_discovery_repository()
            second = shared.initialize_discovery_repository()

            assert first is repository
            assert second is repository
            repository_cls.assert_called_once_with("/tmp/stars-discovery.db")
    finally:
        shared.discovery_repository = original
