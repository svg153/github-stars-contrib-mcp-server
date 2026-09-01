"""MCP tool for idempotent REST upsert of a GitHub Stars contribution."""

from __future__ import annotations

from datetime import datetime

import structlog
from pydantic import BaseModel, HttpUrl, ValidationError

from ..application.use_cases.upsert_contribution import UpsertContribution
from ..di.container import get_stars_api
from ..models import ContributionType
from ..shared import mcp
from ..utils.normalization import normalize_description

logger = structlog.get_logger(__name__)


class UpsertContributionInput(BaseModel):
    title: str
    url: HttpUrl
    description: str | None = None
    type: ContributionType
    date: datetime


async def upsert_contribution_impl(client_id: str, data: dict) -> dict:
    """Validate a complete payload and execute REST PUT /{clientId}."""
    logger.info("Upserting contribution", client_id=client_id, data=data)
    try:
        payload = UpsertContributionInput(**data)
    except ValidationError as exc:
        return {"success": False, "error": exc.errors()}

    upsert_data = payload.model_dump()
    upsert_data["date"] = payload.date.isoformat()
    upsert_data["url"] = str(payload.url)
    upsert_data["type"] = payload.type.value
    upsert_data["description"] = normalize_description(payload.description)

    try:
        result = await UpsertContribution(get_stars_api())(client_id, upsert_data)
        return {"success": True, "data": result.get("upsertContribution")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def upsert_contribution(client_id: str, data: dict) -> dict:
    """Create or replace one contribution idempotently using a stable client ID.

    `data` must contain the complete contribution: title, url, type, date and
    optional description. This is not the retired partial GraphQL update.

    `client_id` is caller-controlled. Do not pass a legacy server-generated
    contribution ID unless it was originally chosen by your client as the
    REST client ID.
    """
    return await upsert_contribution_impl(client_id, data)
