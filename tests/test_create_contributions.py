import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from github_stars_contrib_mcp.tools.create_contributions import create_contributions_impl
from github_stars_contrib_mcp import shared


@pytest.mark.asyncio
async def test_create_contributions_valid(monkeypatch):
    # Mock client
    mock_client = AsyncMock()
    mock_client.create_contributions.return_value = type(
        "Res", (), {"ok": True, "ids": ["1", "2"], "error": None}
    )()
    shared.stars_client = mock_client

    data = [
        {
            "title": "Test",
            "url": "https://example.com",
            "description": "d",
            "type": "BLOGPOST",
            "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
        }
    ]

    res = await create_contributions_impl(data=data)
    assert res["success"] is True
    assert res["ids"] == ["1", "2"]


@pytest.mark.asyncio
async def test_create_contributions_invalid_url():
    shared.stars_client = None
    data = [{
        "title": "Test",
        "url": "not-a-url",
        "type": "BLOGPOST",
        "date": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
    }]
    res = await create_contributions_impl(data=data)
    assert res["success"] is False
