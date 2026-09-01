"""MCP server entry point for Stars Contributions."""

import asyncio
import os
import sys

import structlog

from .config.settings import settings
from .shared import mcp

# Importing tool modules registers their decorators on the shared MCPServer.
from .tools import (  # noqa: F401,E402
    create_contribution,
    create_contributions,
    create_link,
    delete_link,
    get_stars,
    get_user,
    get_user_data,
    list_contributions,
    update_contributions,
    update_link,
    update_profile,
)

logger = structlog.get_logger(__name__)


async def initialize_server() -> None:
    from .shared import initialize_stars_client

    await initialize_stars_client()


def main() -> None:
    logger.info("Starting Stars Contributions MCP Server", log_level=settings.log_level)

    try:

        async def _init_with_timeout() -> None:
            try:
                await asyncio.wait_for(initialize_server(), timeout=2)
            except TimeoutError:
                logger.warning(
                    "Stars client initialization timed out; continuing without validation"
                )

        asyncio.run(_init_with_timeout())
    except Exception as exc:
        logger.error("Unexpected failure before MCP run", error=str(exc))
        sys.exit(1)
        return

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8766"))
    path = os.getenv("MCP_PATH", "/mcp")
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    # Keep the historical "http" alias, but serve the current MCP transport.
    if transport == "http":
        transport = "streamable-http"

    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            streamable_http_path=path,
            stateless_http=True,
        )
    elif transport == "sse":
        # SSE remains only for legacy clients; Streamable HTTP is preferred.
        mcp.run(transport="sse", host=host, port=port, sse_path=path)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
