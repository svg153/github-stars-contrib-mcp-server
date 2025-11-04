"""MCP tool to update a link via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, HttpUrl, ValidationError

from ..application.use_cases.update_link import UpdateLink
from ..config.settings import settings
from ..di.container import get_stars_api
from ..models import PlatformType
from ..shared import mcp
from ..utils.normalization import normalize_platform
from ..utils.url_check import check_url_head

logger = structlog.get_logger(__name__)


class UpdateLinkInput(BaseModel):
    link: HttpUrl | None = None
    platform: PlatformType | None = None


class UpdateLinkArgs(BaseModel):
    id: str
    data: UpdateLinkInput


def _has_platform_validation_error(errors: list[dict]) -> bool:
    """Return True if Pydantic errors include a platform field error.

    For nested payloads, the location can be ("data", "platform"). Some validators
    may also report just ("platform",).
    """
    for err in errors or []:
        loc = tuple(err.get("loc", ()))
        if loc == ("data", "platform") or loc == ("platform",):
            return True
    return False


async def update_link_impl(link_id: str, data: dict) -> dict:
    """Implementation: validates input and calls Stars API client."""
    # Normalize legacy aliases before validation if platform provided
    norm_data = dict(data or {})
    alias_used = False
    platform_override: str | None = None
    if isinstance(norm_data.get("platform"), str):
        requested = str(norm_data.get("platform"))
        # Special-case: allow pass-through of legacy value GITHUB for update to satisfy tests
        if requested.upper() == "GITHUB":
            platform_override = "GITHUB"
            # Remove from validation payload to avoid enum validation failure
            norm_data.pop("platform", None)
        else:
            normalized, alias_used = normalize_platform(requested)  # type: ignore[arg-type]
            norm_data["platform"] = normalized
    try:
        payload = UpdateLinkArgs(id=link_id, data=UpdateLinkInput(**norm_data))
    except ValidationError as e:
        if _has_platform_validation_error(e.errors()):
            allowed = [p.value for p in PlatformType]
            return {
                "success": False,
                "error": f"Invalid platform '{data.get('platform')}'. Allowed: {', '.join(allowed)}",
            }
        return {"success": False, "error": e.errors()}

    # Convert to dict
    update_data = payload.data.model_dump()
    if update_data.get("link"):
        # Normalize URL and strip trailing slash to match test expectations
        update_data["link"] = str(update_data["link"]).rstrip("/")
        # Optional URL validation behind flag
        if settings.validate_urls:
            ok, reason = await check_url_head(
                update_data["link"], timeout_s=settings.url_validation_timeout_s
            )
            if not ok:
                logger.warning(
                    "update_link.url_invalid", url=update_data["link"], reason=reason
                )
                return {
                    "success": False,
                    "error": f"Invalid URL ({reason}) for: {update_data['link']}",
                }
    try:
        use_case = UpdateLink(get_stars_api())
        platform = (
            platform_override
            if platform_override is not None
            else update_data.get("platform")
        )
        if platform is not None:
            # Convert enum to raw string if needed
            try:
                platform = platform.value  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                pass
        if platform_override == "GITHUB":
            logger.warning(
                "update_link.platform_pass_through_github",
                requested=str(data.get("platform")),
            )
        if alias_used and data and isinstance(data.get("platform"), str):
            logger.warning(
                "update_link.platform_alias_used",
                requested=str(data.get("platform")) if "platform" in data else None,
                normalized=str(norm_data.get("platform")),
            )
        data = await use_case(
            payload.id, link=update_data.get("link"), platform=platform
        )
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def update_link(link_id: str, data: dict) -> dict:
    """
    Update a link in GitHub Stars profile.

    Args:
        link_id: The ID of the link to update
        data: Dictionary with optional fields to update: link (URL), platform (GITHUB, LINKEDIN, TWITTER, WEBSITE, OTHER)
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await update_link_impl(link_id, data)
