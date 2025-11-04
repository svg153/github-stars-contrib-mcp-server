"""Tests for advanced features tools."""

from unittest.mock import AsyncMock, patch

import pytest

from github_stars_contrib_mcp.tools.compare_contributions import (
    compare_contributions_impl,
)
from github_stars_contrib_mcp.tools.export_contributions import (
    export_contributions_impl,
)
from github_stars_contrib_mcp.tools.get_contributions_stats import (
    get_contributions_stats_impl,
)

# Sample test data
SAMPLE_CONTRIBUTIONS = {
    "publicProfile": {
        "contributions": [
            {
                "title": "Blog Post 1",
                "type": "BLOGPOST",
                "date": "2024-01-15T10:00:00Z",
                "url": "https://example.com/blog/1",
                "description": "My first blog",
            },
            {
                "title": "Talk at Conf",
                "type": "SPEAKING",
                "date": "2024-02-20T14:00:00Z",
                "url": "https://example.com/talk",
                "description": None,
            },
            {
                "title": "Blog Post 2",
                "type": "BLOGPOST",
                "date": "2024-03-10T09:00:00Z",
                "url": "https://example.com/blog/2",
                "description": "Second blog",
            },
            {
                "title": "Open Source PR",
                "type": "OPEN_SOURCE",
                "date": "2023-12-05T16:00:00Z",
                "url": "https://github.com/project",
                "description": None,
            },
        ]
    }
}


class TestGetContributionsStats:
    @pytest.mark.asyncio
    async def test_stats_total(self):
        """Test getting total statistics."""
        with patch(
            "github_stars_contrib_mcp.tools.get_contributions_stats.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.get_contributions_stats.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await get_contributions_stats_impl({"username": "testuser"})

                assert result["success"] is True
                assert result["data"]["total_count"] == 4
                assert result["data"]["by_type"]["BLOGPOST"] == 2
                assert result["data"]["by_type"]["SPEAKING"] == 1
                assert result["data"]["by_type"]["OPEN_SOURCE"] == 1

    @pytest.mark.asyncio
    async def test_stats_group_by_type(self):
        """Test grouping statistics by type."""
        with patch(
            "github_stars_contrib_mcp.tools.get_contributions_stats.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.get_contributions_stats.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await get_contributions_stats_impl({
                    "username": "testuser",
                    "group_by": "type",
                })

                assert result["success"] is True
                assert "BLOGPOST" in result["data"]["grouped"]
                assert "SPEAKING" in result["data"]["grouped"]
                assert len(result["data"]["grouped"]["BLOGPOST"]) == 2

    @pytest.mark.asyncio
    async def test_stats_group_by_month(self):
        """Test grouping statistics by month."""
        with patch(
            "github_stars_contrib_mcp.tools.get_contributions_stats.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.get_contributions_stats.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await get_contributions_stats_impl({
                    "username": "testuser",
                    "group_by": "month",
                })

                assert result["success"] is True
                grouped = result["data"]["grouped"]
                assert "2024-01" in grouped
                assert "2024-02" in grouped
                assert grouped["2024-01"]["count"] == 1

    @pytest.mark.asyncio
    async def test_stats_empty_contributions(self):
        """Test stats with no contributions."""
        with patch(
            "github_stars_contrib_mcp.tools.get_contributions_stats.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = {"publicProfile": {"contributions": []}}

            with patch(
                "github_stars_contrib_mcp.tools.get_contributions_stats.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await get_contributions_stats_impl({"username": "testuser"})

                assert result["success"] is True
                assert result["data"]["total_count"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_mcp_ui(self):
        """Test stats with MCP-UI visualization."""
        with patch(
            "github_stars_contrib_mcp.tools.get_contributions_stats.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.get_contributions_stats.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await get_contributions_stats_impl({
                    "username": "testuser",
                    "include_ui": True,
                })

                # Result should be a list of UIResource
                assert isinstance(result, list)
                assert len(result) > 0

                ui_resource = result[0]
                assert hasattr(ui_resource, "resource")
                assert str(ui_resource.resource.uri).startswith("ui://")
                assert "text/html" in ui_resource.resource.mimeType
                assert ui_resource.resource.text is not None
                assert "<html" in ui_resource.resource.text.lower()
                assert "plotly" in ui_resource.resource.text.lower()


class TestExportContributions:
    @pytest.mark.asyncio
    async def test_export_json(self):
        """Test exporting as JSON."""
        with patch(
            "github_stars_contrib_mcp.tools.export_contributions.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.export_contributions.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await export_contributions_impl({
                    "username": "testuser",
                    "format": "json",
                })

                assert result["success"] is True
                assert result["data"]["format"] == "json"
                assert result["data"]["count"] == 4
                # Parse JSON to ensure it's valid
                import json

                parsed = json.loads(result["data"]["content"])
                assert len(parsed) == 4

    @pytest.mark.asyncio
    async def test_export_csv(self):
        """Test exporting as CSV."""
        with patch(
            "github_stars_contrib_mcp.tools.export_contributions.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.export_contributions.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await export_contributions_impl({
                    "username": "testuser",
                    "format": "csv",
                })

                assert result["success"] is True
                assert result["data"]["format"] == "csv"
                content = result["data"]["content"]
                lines = content.strip().split("\n")
                assert len(lines) == 5  # Header + 4 rows

    @pytest.mark.asyncio
    async def test_export_markdown(self):
        """Test exporting as Markdown."""
        with patch(
            "github_stars_contrib_mcp.tools.export_contributions.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.export_contributions.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await export_contributions_impl({
                    "username": "testuser",
                    "format": "markdown",
                })

                assert result["success"] is True
                assert result["data"]["format"] == "markdown"
                content = result["data"]["content"]
                assert "@testuser" in content
                assert "Blog Post 1" in content

    @pytest.mark.asyncio
    async def test_export_with_sort(self):
        """Test exporting with sort."""
        with patch(
            "github_stars_contrib_mcp.tools.export_contributions.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()
            mock_use_case.return_value = SAMPLE_CONTRIBUTIONS

            with patch(
                "github_stars_contrib_mcp.tools.export_contributions.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await export_contributions_impl({
                    "username": "testuser",
                    "format": "json",
                    "sort_by": "date",
                })

                assert result["success"] is True
                import json

                parsed = json.loads(result["data"]["content"])
                # Check that dates are in descending order
                dates = [p["date"] for p in parsed]
                assert dates == sorted(dates, reverse=True)


class TestCompareContributions:
    @pytest.mark.asyncio
    async def test_compare_total(self):
        """Test comparing total contributions."""
        with patch(
            "github_stars_contrib_mcp.tools.compare_contributions.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()

            # Different data for each user
            user1_data = SAMPLE_CONTRIBUTIONS
            user2_data = {
                "publicProfile": {
                    "contributions": [
                        {
                            "title": "Talk",
                            "type": "SPEAKING",
                            "date": "2024-01-10T10:00:00Z",
                            "url": "https://example.com/talk2",
                        }
                    ]
                }
            }

            mock_use_case.side_effect = [user1_data, user2_data]

            with patch(
                "github_stars_contrib_mcp.tools.compare_contributions.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await compare_contributions_impl({
                    "username1": "user1",
                    "username2": "user2",
                    "metric": "total",
                })

                assert result["success"] is True
                assert result["data"]["user1_count"] == 4
                assert result["data"]["user2_count"] == 1
                assert result["data"]["comparison"]["difference"] == 3

    @pytest.mark.asyncio
    async def test_compare_by_type(self):
        """Test comparing by type."""
        with patch(
            "github_stars_contrib_mcp.tools.compare_contributions.get_stars_api"
        ) as mock_api:
            mock_use_case = AsyncMock()

            user1_data = SAMPLE_CONTRIBUTIONS
            user2_data = {
                "publicProfile": {
                    "contributions": [
                        {
                            "title": "Blog",
                            "type": "BLOGPOST",
                            "date": "2024-01-10T10:00:00Z",
                            "url": "https://example.com/blog",
                        }
                    ]
                }
            }

            mock_use_case.side_effect = [user1_data, user2_data]

            with patch(
                "github_stars_contrib_mcp.tools.compare_contributions.GetStars"
            ) as mock_get_stars:
                mock_get_stars.return_value = mock_use_case

                result = await compare_contributions_impl({
                    "username1": "user1",
                    "username2": "user2",
                    "metric": "by_type",
                })

                assert result["success"] is True
                by_type = result["data"]["comparison"]["by_type"]
                assert by_type["BLOGPOST"]["user1"] == 2
                assert by_type["BLOGPOST"]["user2"] == 1

    @pytest.mark.asyncio
    async def test_compare_same_user_error(self):
        """Test that comparing same user fails."""
        result = await compare_contributions_impl({
            "username1": "user",
            "username2": "user",
        })

        assert result["success"] is False
        assert "Cannot compare user with themselves" in result["error"]
