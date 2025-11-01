"""GitHub Stars MCP utilities."""

from .models import APIResult
from .queries import *
from .stars_client import StarsClient

__all__ = ["APIResult", "StarsClient"]