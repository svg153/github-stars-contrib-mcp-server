"""Unit tests for server module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from github_stars_contrib_mcp import server


class TestServer:
    @patch("os.getenv")
    @patch("github_stars_contrib_mcp.server.mcp")
    @patch("github_stars_contrib_mcp.server.logger")
    @patch("github_stars_contrib_mcp.server.settings")
    def test_main(self, mock_settings, mock_logger, mock_mcp, mock_getenv):
        mock_settings.stars_api_token = "test_token"
        mock_settings.log_level = "INFO"
        mock_getenv.side_effect = lambda key, default=None: {
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": "8766",
            "MCP_PATH": "/mcp"
        }.get(key, default)
        
        with patch("github_stars_contrib_mcp.server.initialize_server", new_callable=AsyncMock):
            server.main()
        
        mock_logger.info.assert_called_once_with("Starting Stars Contributions MCP Server", log_level="INFO")
        mock_mcp.run.assert_called_once_with(transport="stdio")