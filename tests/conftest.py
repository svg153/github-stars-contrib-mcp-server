"""Shared pytest fixtures and configuration."""

from unittest.mock import AsyncMock

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.utils.stars_client import StarsClient


@pytest.fixture
def mock_stars_client():
    """Mock StarsClient for unit tests."""
    return AsyncMock(spec=StarsClient)


@pytest.fixture
def mock_shared_client(mock_stars_client):
    """Set up shared.stars_client with a mock for one test."""
    original = shared.stars_client
    shared.stars_client = mock_stars_client
    yield mock_stars_client
    shared.stars_client = original
