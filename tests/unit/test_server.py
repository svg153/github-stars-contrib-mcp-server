"""Server bootstrap tests for the MCP SDK 2.x migration."""

from unittest.mock import AsyncMock, patch

from github_stars_contrib_mcp import server


@patch("os.getenv")
@patch("github_stars_contrib_mcp.server.mcp")
@patch("github_stars_contrib_mcp.server.logger")
def test_main_defaults_to_stdio(mock_logger, mock_mcp, mock_getenv):
    mock_getenv.side_effect = lambda key, default=None: default
    with patch.object(server, "initialize_server", new_callable=AsyncMock):
        server.main()
    mock_mcp.run.assert_called_once_with(transport="stdio")


@patch("os.getenv")
@patch("github_stars_contrib_mcp.server.mcp")
@patch("github_stars_contrib_mcp.server.logger")
def test_http_alias_runs_streamable_http(mock_logger, mock_mcp, mock_getenv):
    values = {
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": "9999",
        "MCP_PATH": "/mcp",
        "MCP_TRANSPORT": "http",
    }
    mock_getenv.side_effect = lambda key, default=None: values.get(key, default)
    with patch.object(server, "initialize_server", new_callable=AsyncMock):
        server.main()
    mock_mcp.run.assert_called_once_with(
        transport="streamable-http",
        host="0.0.0.0",
        port=9999,
        streamable_http_path="/mcp",
        stateless_http=True,
    )
