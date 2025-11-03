"""Unit tests for server module."""

from unittest.mock import AsyncMock, patch

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

    @patch("os.getenv")
    @patch("github_stars_contrib_mcp.server.mcp")
    @patch("github_stars_contrib_mcp.server.logger")
    @patch("github_stars_contrib_mcp.server.settings")
    def test_main_http_transport(self, mock_settings, mock_logger, mock_mcp, mock_getenv):
        mock_settings.stars_api_token = None
        mock_settings.log_level = "INFO"
        # Force HTTP transport branch and allow startup without token
        def getenv_side(key, default=None):
            values = {
                "MCP_HOST": "0.0.0.0",
                "MCP_PORT": "9999",
                "MCP_PATH": "/mcp",
                "MCP_TRANSPORT": "http",
                "DANGEROUSLY_OMIT_AUTH": "true",
            }
            return values.get(key, default)

        mock_getenv.side_effect = getenv_side

        # Avoid actually initializing network clients
        from github_stars_contrib_mcp import server as server_mod
        with patch.object(server_mod, "initialize_server", new_callable=AsyncMock):
            server_mod.main()

        mock_mcp.run.assert_called_once_with(transport="http", host="0.0.0.0", port=9999, path="/mcp")

    @patch("os.getenv")
    @patch("github_stars_contrib_mcp.server.mcp")
    @patch("github_stars_contrib_mcp.server.logger")
    @patch("github_stars_contrib_mcp.server.settings")
    def test_main_initialization_error_exits(self, mock_settings, mock_logger, mock_mcp, mock_getenv):
        mock_settings.log_level = "INFO"
        mock_getenv.side_effect = lambda key, default=None: default

        from github_stars_contrib_mcp import server as server_mod

        async def failing_init():
            raise RuntimeError("boom")

        with patch.object(server_mod, "initialize_server", new=AsyncMock(side_effect=failing_init)):
            with patch("sys.exit") as mock_exit:
                server_mod.main()
                mock_exit.assert_called_once_with(1)
