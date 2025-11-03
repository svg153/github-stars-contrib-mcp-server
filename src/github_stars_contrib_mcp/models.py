"""Data models for GitHub Stars Contributions MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ContributionType(str, Enum):
    # Based on GitHub Stars UI options
    SPEAKING = "SPEAKING"
    BLOGPOST = "BLOGPOST"
    ARTICLE_PUBLICATION = "ARTICLE_PUBLICATION"
    EVENT_ORGANIZATION = "EVENT_ORGANIZATION"
    HACKATHON = "HACKATHON"
    OPEN_SOURCE_PROJECT = "OPEN_SOURCE_PROJECT"
    VIDEO_PODCAST = "VIDEO_PODCAST"
    FORUM = "FORUM"
    OTHER = "OTHER"


# Migration note: The values 'GITHUB' and 'WEBSITE' have been removed from PlatformType.
# If your code previously relied on these, review usages and update to supported platforms.

class PlatformType(str, Enum):
    # Based on live GitHub Stars API enum PlatformType
    TWITTER = "TWITTER"
    MEDIUM = "MEDIUM"
    LINKEDIN = "LINKEDIN"
    README = "README"
    STACK_OVERFLOW = "STACK_OVERFLOW"
    DEV_TO = "DEV_TO"
    MASTODON = "MASTODON"
    OTHER = "OTHER"


class ContributionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    url: HttpUrl
    description: str | None = None
    type: ContributionType
    date: datetime


class CreateContributionsResponseItem(BaseModel):
    id: str


class CreateContributionsResponse(BaseModel):
    success: bool = Field(description="Whether the API call was successful")
    ids: list[str] = Field(default_factory=list)
    error: str | None = None


class DeleteContributionsResponse(BaseModel):
    success: bool = Field(description="Whether the API call was successful")
    ids: list[str] = Field(default_factory=list)
    error: str | None = None


class PlaygroundAuthHeader(BaseModel):
    key: Literal["Authorization"] = "Authorization"
    value: str = Field(description="Bearer <STARS_API_TOKEN>")


class ContributionUpdateInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    type: ContributionType | None = None
    date: datetime | None = None


class UpdateContributionResponse(BaseModel):
    success: bool = Field(description="Whether the API call was successful")
    data: dict | None = None
    error: str | None = None


class DeleteContributionResponse(BaseModel):
    success: bool = Field(description="Whether the API call was successful")
    data: dict | None = None
    error: str | None = None


class LinkItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    link: HttpUrl
    platform: PlatformType


class CreateLinkResponse(BaseModel):
    success: bool = Field(description="Whether the API call was successful")
    data: dict | None = None
    error: str | None = None


class ProfileUpdateInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    avatar: str | None = None
    name: str | None = None
    bio: str | None = None
    country: str | None = None
    birthdate: datetime | None = None
    reason: str | None = None
    jobTitle: str | None = None
    company: str | None = None
    phoneNumber: str | None = None
    address: str | None = None
    state: str | None = None
    city: str | None = None
    zipcode: str | None = None


class UpdateProfileResponse(BaseModel):
    success: bool = Field(description="Whether the API call was successful")
    data: dict | None = None
    error: str | None = None
