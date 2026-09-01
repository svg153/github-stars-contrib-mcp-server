"""Tests for statistics, export, and comparison tools."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp.tools.compare_contributions import (
    compare_contributions_impl,
)
from github_stars_contrib_mcp.tools.export_contributions import export_contributions_impl
from github_stars_contrib_mcp.tools.get_contributions_stats import (
    get_contributions_stats_impl,
)

SAMPLE = {
    "publicProfile": {
        "contributions": [
            {
                "title": "Blog 1",
                "type": "BLOGPOST",
                "date": "2024-01-15T10:00:00Z",
                "url": "https://example.com/1",
            },
            {
                "title": "Talk",
                "type": "SPEAKING",
                "date": "2024-02-20T14:00:00Z",
                "url": "https://example.com/talk",
            },
            {
                "title": "Blog 2",
                "type": "BLOGPOST",
                "date": "2024-03-10T09:00:00Z",
                "url": "https://example.com/2",
            },
        ]
    }
}


@pytest.mark.asyncio
async def test_stats_total_and_grouping():
    use_case = AsyncMock(return_value=SAMPLE)
    with patch(
        "github_stars_contrib_mcp.tools.get_contributions_stats.GetStars",
        return_value=use_case,
    ):
        result = await get_contributions_stats_impl(
            {"username": "testuser", "group_by": "type"}
        )
    assert result["success"] is True
    assert result["data"]["total_count"] == 3
    assert result["data"]["by_type"]["BLOGPOST"] == 2
    assert len(result["data"]["grouped"]["BLOGPOST"]) == 2


@pytest.mark.asyncio
async def test_stats_ui_returns_resource():
    use_case = AsyncMock(return_value=SAMPLE)
    with patch(
        "github_stars_contrib_mcp.tools.get_contributions_stats.GetStars",
        return_value=use_case,
    ):
        result = await get_contributions_stats_impl(
            {"username": "testuser", "include_ui": True}
        )
    assert isinstance(result, list)
    assert str(result[0].resource.uri).startswith("ui://")


@pytest.mark.asyncio
@pytest.mark.parametrize("format_name", ["json", "csv", "markdown"])
async def test_export_formats(format_name: str):
    use_case = AsyncMock(return_value=SAMPLE)
    with patch(
        "github_stars_contrib_mcp.tools.export_contributions.GetStars",
        return_value=use_case,
    ):
        result = await export_contributions_impl(
            {"username": "testuser", "format": format_name}
        )
    assert result["success"] is True
    assert result["data"]["count"] == 3
    assert result["data"]["content"]
    if format_name == "json":
        assert len(json.loads(result["data"]["content"])) == 3


@pytest.mark.asyncio
async def test_compare_total():
    other = {
        "publicProfile": {
            "contributions": [SAMPLE["publicProfile"]["contributions"][0]]
        }
    }
    use_case = AsyncMock(side_effect=[SAMPLE, other])
    with patch(
        "github_stars_contrib_mcp.tools.compare_contributions.GetStars",
        return_value=use_case,
    ):
        result = await compare_contributions_impl(
            {"username1": "one", "username2": "two", "metric": "total"}
        )
    assert result["success"] is True
    assert result["data"]["comparison"]["difference"] == 2


@pytest.mark.asyncio
async def test_compare_same_user_is_rejected():
    result = await compare_contributions_impl(
        {"username1": "same", "username2": "same"}
    )
    assert result["success"] is False
