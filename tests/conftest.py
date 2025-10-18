"""Shared pytest fixtures and configuration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.utils.stars_client import StarsClient


@pytest.fixture
def mock_stars_client():
    """Mock StarsClient for unit tests."""
    client = AsyncMock(spec=StarsClient)
    return client


@pytest.fixture
def mock_shared_client(mock_stars_client):
    """Set up shared.stars_client with mock."""
    original = shared.stars_client
    shared.stars_client = mock_stars_client
    yield mock_stars_client
    shared.stars_client = original


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing HTTP calls."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Default response for get_user_data
    mock_resp.json.return_value = {"data": {"loggedUser": {"id": "test"}}}
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    return mock_client


@pytest.fixture
def mock_httpx_client_create_contributions():
    """Mock httpx.AsyncClient specifically for create_contributions tests."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Response for create_contributions
    mock_resp.json.return_value = {"data": {"createContributions": [{"id": "1"}, {"id": "2"}]}}
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    return mock_client