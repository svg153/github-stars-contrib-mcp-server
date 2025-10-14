"""MCP server entry point for Stars Contributions."""

import sys

# Prevent stdout conflicts with MCP protocol during import
_original_stdout = sys.stdout
sys.stdout = sys.stderr
import structlog

sys.stdout = _original_stdout

from .config import settings
from .shared import mcp

# Register tools
from .tools import create_contributions  # noqa: F401
from .tools import get_user_data  # noqa: F401

logger = structlog.get_logger(__name__)


async def initialize_server() -> None:
    from .shared import initialize_stars_client

    await initialize_stars_client()


import asyncio

try:
    loop = asyncio.get_running_loop()
    asyncio.create_task(initialize_server())
except RuntimeError:
    asyncio.run(initialize_server())


def main() -> None:
    import os

    logger.info("Starting Stars Contributions MCP Server", log_level=settings.log_level)
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8766"))
    path = os.getenv("MCP_PATH", "/mcp")
    mcp.run(transport="streamable-http", host=host, port=port, path=path)


if __name__ == "__main__":
    main()
