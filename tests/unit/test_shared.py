"""Unit tests for shared module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from github_stars_contrib_mcp import shared


@pytest.fixture
def mock_shared_client():
    """Fixture to mock the shared client."""
    with patch("github_stars_contrib_mcp.shared.StarsClient") as mock_client_class:
        yield mock_client_class


class TestShared:
    @pytest.mark.asyncio
    async def test_initialize_stars_client_no_token(self, mock_shared_client):
        with patch("github_stars_contrib_mcp.shared.settings") as mock_settings:
            mock_settings.stars_api_token = None
            await shared.initialize_stars_client()
            assert shared.stars_client is None

    @pytest.mark.asyncio
    async def test_initialize_stars_client_with_token(self, mock_shared_client):
        with patch("github_stars_contrib_mcp.shared.settings") as mock_settings:
            mock_settings.stars_api_token = "test_token"
            mock_client = AsyncMock()
            mock_client.get_user_data.return_value = {"ok": True, "data": {"loggedUser": {"id": "test"}}}
            mock_shared_client.return_value = mock_client
            await shared.initialize_stars_client()
            assert shared.stars_client == mock_client
            mock_shared_client.assert_called_once_with(api_url="https://api-stars.github.com/", token="test_token")

    @pytest.mark.asyncio
    async def test_initialize_stars_client_exception(self, mock_shared_client):
        with patch("github_stars_contrib_mcp.shared.settings") as mock_settings:
            mock_settings.stars_api_token = "test_token"
            mock_shared_client.side_effect = Exception("Test error")
            with pytest.raises(Exception, match="Test error"):
                await shared.initialize_stars_client()

    def test_configure_logging(self):
        # Test that _configure_logging sets up logging when not configured
        with patch("logging.getLogger") as mock_get_logger, \
             patch("sys.stderr") as mock_stderr:
            mock_root = MagicMock()
            mock_root.handlers = []
            mock_get_logger.return_value = mock_root
            
            # Call the function
            shared._configure_logging()
            
            # Check that handler was added
            mock_root.addHandler.assert_called()
            mock_root.setLevel.assert_called()