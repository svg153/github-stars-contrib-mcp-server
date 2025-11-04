"""Minimal DI container functions to construct services."""

from __future__ import annotations

from ..config.settings import Settings
from ..infrastructure.adapters.stars_api_graphql import StarsAPIAdapter
from ..utils.stars_client import StarsClient
from . import __init__ as _di_pkg  # noqa: F401  # Ensure package recognized


def get_settings() -> Settings:
    return Settings()


def get_stars_client(settings: Settings | None = None) -> StarsClient:
    settings = settings or get_settings()
    token = settings.stars_api_token or ""
    return StarsClient(api_url=settings.stars_api_url, token=token)


def get_stars_api(settings: Settings | None = None) -> StarsAPIAdapter:
    client = get_stars_client(settings)
    return StarsAPIAdapter(client)
