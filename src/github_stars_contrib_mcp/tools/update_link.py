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
    """Return True if Pydantic errors include a platform field error."""
    for err in errors or []:
        loc = tuple(err.get("loc", ()))
        if loc in {("data", "platform"), ("platform",)}:
            return True
    return False


async def update_link_impl(link_id: str, data: dict) -> dict:
    """Validate input, normalize legacy aliases, and call the Stars API client."""
    norm_data = dict(data or {})
    alias_used = False
    if isinstance(norm_data.get("platform"), str):
        requested = str(norm_data["platform"])
        normalized, alias_used = normalize_platform(requested)
        norm_data["platform"] = normalized

    try:
        payload = UpdateLinkArgs(id=link_id, data=UpdateLinkInput(**norm_data))
    except ValidationError as exc:
        if _has_platform_validation_error(exc.errors()):
            allowed = [platform.value for platform in PlatformType]
            return {
                "success": False,
                "data": None,
                "error": (
                    f"Invalid platform '{data.get('platform')}'. "
                    f"Allowed: {', '.join(allowed)}"
                ),
            }
        return {"success": False, "data": None, "error": exc.errors()}

    update_data = payload.data.model_dump()
    if update_data.get("link"):
        update_data["link"] = str(update_data["link"]).rstrip("/")
        if settings.validate_urls:
            ok, reason = await check_url_head(
                update_data["link"], timeout_s=settings.url_validation_timeout_s
            )
            if not ok:
                logger.warning(
                    "update_link.url_invalid",
                    url=update_data["link"],
                    reason=reason,
                )
                return {
                    "success": False,
                    "data": None,
                    "error": f"Invalid URL ({reason}) for: {update_data['link']}",
                }

    platform = update_data.get("platform")
    if isinstance(platform, PlatformType):
        platform = platform.value

    if alias_used:
        logger.warning(
            "update_link.platform_alias_used",
            requested=str(data.get("platform")),
            normalized=str(platform),
        )

    try:
        use_case = UpdateLink(get_stars_api())
        result = await use_case(
            payload.id,
            link=update_data.get("link"),
            platform=platform,
        )
        return {"success": True, "data": result, "error": None}
    except Exception as exc:
        return {"success": False, "data": None, "error": str(exc)}


@mcp.tool()
async def update_link(link_id: str, data: dict) -> dict:
    """
    Update a link in the GitHub Stars profile.

    Legacy aliases are normalized consistently: GITHUB -> README and WEBSITE -> OTHER.
    """
    return await update_link_impl(link_id, data)
