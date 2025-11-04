"""MCP tool to update profile via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ValidationError

from ..application.use_cases.update_profile import UpdateProfile
from ..di.container import get_stars_api
from ..models import ProfileUpdateInput
from ..shared import mcp

logger = structlog.get_logger(__name__)


class UpdateProfileArgs(BaseModel):
    data: ProfileUpdateInput


async def update_profile_impl(data: dict) -> dict:
    """Implementation: validates input and calls Stars API client."""
    logger.info("Updating profile", data=data)
    try:
        payload = UpdateProfileArgs(data=ProfileUpdateInput(**data))
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    # Convert to dict, handling datetime
    update_data = payload.data.model_dump()
    if update_data.get("birthdate"):
        update_data["birthdate"] = update_data["birthdate"].isoformat()
    try:
        use_case = UpdateProfile(get_stars_api())
        data = await use_case(update_data)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
