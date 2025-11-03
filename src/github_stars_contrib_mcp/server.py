"""MCP server entry point for Stars Contributions."""

import asyncio
import sys

# Prevent stdout conflicts with MCP protocol during import
_original_stdout = sys.stdout
sys.stdout = sys.stderr
import structlog

sys.stdout = _original_stdout

from .config.settings import settings
from .shared import mcp

# Register tools
from .tools import (
    create_contributions,  # noqa: F401
    create_link,  # noqa: F401
    delete_contributions,  # noqa: F401
    delete_link,  # noqa: F401
    get_stars,  # noqa: F401
    get_user,  # noqa: F401
    get_user_data,  # noqa: F401
    update_contributions,  # noqa: F401
    update_link,  # noqa: F401
    update_profile,  # noqa: F401
)

logger = structlog.get_logger(__name__)


async def initialize_server() -> None:
    from .shared import initialize_stars_client

    await initialize_stars_client()


def main() -> None:
    import os

    logger.info("Starting Stars Contributions MCP Server", log_level=settings.log_level)

    try:
        # Do not block server startup on external network calls.
        # Attempt initialization briefly; if it times out or fails, continue so MCP can respond to initialize.
        async def _init_with_timeout():
            try:
                await asyncio.wait_for(initialize_server(), timeout=2)
            except asyncio.TimeoutError:
                logger.warning("Stars client initialization timed out; continuing without validation")
            except Exception:
                # Propagate non-timeout failures to trigger a clean exit as before.
                raise

        asyncio.run(_init_with_timeout())
    except Exception as e:
        logger.error("Unexpected failure before MCP run", error=str(e))
        sys.exit(1)

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8766"))
    path = os.getenv("MCP_PATH", "/mcp")
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    # Select transport explicitly to avoid passing HTTP kwargs to stdio runner
    if transport in {"http", "streamable-http", "sse"}:
        mcp.run(transport=transport, host=host, port=port, path=path)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
