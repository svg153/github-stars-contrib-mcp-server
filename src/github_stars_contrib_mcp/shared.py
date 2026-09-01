"""Shared instances and server bootstrap for Stars Contributions MCP Server."""

import logging
import sys

import structlog
from mcp.server import MCPServer

from . import __version__
from .config.settings import settings
from .utils.stars_client import StarsClient


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(name)s - %(levelname)s - %(message)s")
    )
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level))

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.KeyValueRenderer(
                key_order=["timestamp", "level", "event", "logger"]
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


_configure_logging()

mcp = MCPServer(
    name="GitHub Stars Contributions MCP Server",
    version=__version__,
    instructions=(
        "Manage GitHub Stars contributions with the current REST Contributions API. "
        "Use stable caller-controlled client IDs for idempotent upserts. "
        "Contribution deletion is not available through the API."
    ),
)
stars_client: StarsClient | None = None


async def initialize_stars_client() -> None:
    global stars_client
    logger = structlog.get_logger(__name__)
    try:
        if not settings.stars_api_token:
            if not settings.dangerously_omit_auth:
                raise ValueError("STARS_API_TOKEN is required but not provided")
            logger.warning("No STARS_API_TOKEN provided; tools will be disabled")
            stars_client = None
            return

        stars_client = StarsClient(
            api_url=settings.stars_api_url,
            contributions_api_url=settings.stars_contributions_api_url,
            token=settings.stars_api_token,
        )

        # Validate against the supported REST Contributions API, not the retired
        # GraphQL contributions surface.
        result = await stars_client.validate_token()
        if not result.ok:
            raise ValueError(
                f"Invalid STARS_API_TOKEN: {result.error or 'REST validation failed'}"
            )

        logger.info("Stars client initialized and token validated via REST")
    except Exception as exc:
        logger.error("Failed to initialize Stars client", error=str(exc))
        raise
