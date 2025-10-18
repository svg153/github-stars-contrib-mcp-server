"""MCP tool to update profile via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ValidationError

from .. import shared
from ..models import ProfileUpdateInput
from ..shared import mcp

logger = structlog.get_logger(__name__)


class UpdateProfileArgs(BaseModel):
    data: ProfileUpdateInput


async def update_profile_impl(data: dict) -> dict:
    """Implementation: validates input and calls Stars API client."""
    try:
        payload = UpdateProfileArgs(data=ProfileUpdateInput(**data))
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized"}

    # Convert to dict, handling datetime
    update_data = payload.data.model_dump()
    if update_data.get("birthdate"):
        update_data["birthdate"] = update_data["birthdate"].isoformat()

    result = await shared.stars_client.update_profile(update_data)
    if result.get("ok"):
        return {"success": True, "data": result.get("data")}
    return {"success": False, "error": result.get("error")}


@mcp.tool()
async def update_profile(data: dict) -> dict:
    """
    Update the user's profile in GitHub Stars.

    Args:
        data: Dictionary with optional fields to update: avatar, name, bio, country, birthdate (ISO string), reason, jobTitle, company, phoneNumber, address, state, city, zipcode
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await update_profile_impl(data)
