"""Data models for GitHub Stars Contributions MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ContributionType(str, Enum):
    # Based on provided example; extend as needed
    BLOGPOST = "BLOGPOST"
    EVENT = "EVENT"
    TALK = "TALK"
    PR = "PR"
    VIDEO = "VIDEO"


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


class PlaygroundAuthHeader(BaseModel):
    key: Literal["Authorization"] = "Authorization"
    value: str = Field(description="Bearer <STARS_API_TOKEN>")
