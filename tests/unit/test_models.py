"""Unit tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from github_stars_contrib_mcp.models import (
    ContributionItem,
    ContributionType,
    CreateContributionsResponse,
    CreateContributionsResponseItem,
    PlaygroundAuthHeader,
)


class TestContributionType:
    @pytest.mark.parametrize(
        "contribution_type",
        [
            "BLOGPOST",
            "SPEAKING",
            "ARTICLE_PUBLICATION",
            "EVENT_ORGANIZATION",
            "HACKATHON",
            "OPEN_SOURCE_PROJECT",
            "VIDEO_PODCAST",
            "FORUM",
            "OTHER",
        ],
    )
    def test_valid_types(self, contribution_type):
        assert ContributionType(contribution_type) == contribution_type


class TestContributionItem:
    def test_valid_item(self):
        item = ContributionItem(
            title="Test Title",
            url="https://example.com",
            description="Test description",
            type=ContributionType.BLOGPOST,
            date=datetime(2024, 1, 1, 12, 0, 0),
        )
        assert item.title == "Test Title"
        assert str(item.url) == "https://example.com/"
        assert item.description == "Test description"
        assert item.type == ContributionType.BLOGPOST
        assert item.date == datetime(2024, 1, 1, 12, 0, 0)

    def test_minimal_item(self):
        item = ContributionItem(
            title="Test",
            url="https://example.com",
            type=ContributionType.BLOGPOST,
            date=datetime(2024, 1, 1),
        )
        assert item.description is None

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "not-a-url",
            "http://[invalid]",
            "",
        ],
    )
    def test_invalid_url(self, invalid_url):
        with pytest.raises(ValidationError):
            ContributionItem(
                title="Test",
                url=invalid_url,
                type=ContributionType.BLOGPOST,
                date=datetime(2024, 1, 1),
            )

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            ContributionItem(
                title="Test",
                url="https://example.com",
                type="INVALID",
                date=datetime(2024, 1, 1),
            )


class TestCreateContributionsResponse:
    def test_success_response(self):
        response = CreateContributionsResponse(success=True, ids=["1", "2"])
        assert response.success is True
        assert response.ids == ["1", "2"]
        assert response.error is None

    def test_error_response(self):
        response = CreateContributionsResponse(success=False, error="Test error")
        assert response.success is False
        assert response.ids == []
        assert response.error == "Test error"


class TestCreateContributionsResponseItem:
    def test_item(self):
        item = CreateContributionsResponseItem(id="123")
        assert item.id == "123"


class TestPlaygroundAuthHeader:
    def test_header(self):
        header = PlaygroundAuthHeader(value="Bearer token123")
        assert header.key == "Authorization"
        assert header.value == "Bearer token123"

    def test_invalid_key(self):
        with pytest.raises(ValidationError):
            PlaygroundAuthHeader(key="Invalid", value="Bearer token")
