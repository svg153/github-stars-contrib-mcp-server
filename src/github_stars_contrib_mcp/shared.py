"""Shared instances and server bootstrap for Stars Contributions MCP Server."""

import logging
import sys

import structlog

# Redirect stdout to stderr before importing FastMCP
_original_stdout = sys.stdout
sys.stdout = sys.stderr
from fastmcp import FastMCP

sys.stdout = _original_stdout

from .utils.stars_client import StarsClient
from .config import settings


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

mcp = FastMCP("GitHub Stars Contributions MCP Server")

stars_client: StarsClient | None = None


async def initialize_stars_client() -> None:
    global stars_client
    logger = structlog.get_logger(__name__)
    try:
        if not settings.stars_api_token:
            logger.warning("No STARS_API_TOKEN provided; tools will be disabled")
            stars_client = None
            return
        stars_client = StarsClient(api_url="https://api-stars.github.com/", token=settings.stars_api_token)
        logger.info("Stars client initialized")
    except Exception as e:
        logger.error("Failed to initialize Stars client", error=str(e))
        stars_client = None
