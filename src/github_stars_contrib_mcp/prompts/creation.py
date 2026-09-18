"""Prompt that guides an agent through creating a Stars contribution."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl, ValidationError

from ..models import ContributionType
from ..shared import mcp
from .errors import build_error, field_errors_from
from .validation import (
    contribution_type_values,
    parse_optional_date,
    render_field,
)

__all__ = ["ContributionDraft", "contribution_create", "contribution_create_impl"]

_REQUIRED_FIELDS = ("title", "url", "type", "date")


class ContributionDraft(BaseModel):
    """Partial contribution payload; every field is optional at prompt time."""

    title: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    type: ContributionType | None = None
    date: datetime | None = None


def contribution_create_impl(
    *,
    title: str | None = None,
    url: str | None = None,
    description: str | None = None,
    type: str | None = None,  # noqa: A002 - mirrors the MCP tool argument name
    date: str | None = None,
) -> str:
    """Validate the draft and render the creation instructions."""
    try:
        parsed_date = parse_optional_date(date)
    except ValueError as exc:
        return build_error(
            "contribution_create",
            {"date": str(exc)},
            hint="Pass an ISO 8601 date such as 2026-02-14.",
        )

    try:
        draft = ContributionDraft(
            title=title,
            url=url,
            description=description,
            type=ContributionType(type) if type else None,
            date=parsed_date,
        )
    except ValidationError as exc:
        return build_error(
            "contribution_create",
            field_errors_from(exc),
            suggestions={"type": contribution_type_values()},
        )
    except ValueError as exc:
        return build_error(
            "contribution_create",
            {"type": str(exc)},
            suggestions={"type": contribution_type_values()},
            hint="Use one of the suggested ContributionType values.",
        )

    missing = [name for name in _REQUIRED_FIELDS if getattr(draft, name) in (None, "")]

    lines = [
        "Create a GitHub Stars contribution from the draft below.",
        "",
        "Draft:",
        render_field("title", draft.title),
        render_field("url", str(draft.url) if draft.url else None),
        render_field("type", draft.type.value if draft.type else None),
        render_field("date", draft.date.isoformat() if draft.date else None),
        render_field("description", draft.description),
        "",
    ]

    if missing:
        lines.append("Missing required fields: " + ", ".join(missing) + ".")
        lines.append("Ask the user for those values before calling any tool.")
    else:
        lines.append("All required fields are present.")

    lines += [
        "",
        "Next steps:",
        "- Call `create_contribution` with a single `data` object containing "
        "title, url, type, date and the optional description.",
        "- Use `upsert_contribution` with a stable caller-controlled `client_id` "
        "when the write must be idempotent and retryable.",
        "- Never translate a legacy server-generated contribution ID into a REST "
        "`client_id`; `client_id` is always chosen by the caller.",
        "- Contribution deletion is not available through this server.",
    ]
    return "\n".join(lines)


@mcp.prompt()
def contribution_create(  # noqa: A002 - `type` is the documented MCP argument name
    title: str | None = None,
    url: str | None = None,
    description: str | None = None,
    type: str | None = None,
    date: str | None = None,
) -> str:
    """Draft a Stars contribution and explain the REST write to perform."""
    return contribution_create_impl(
        title=title,
        url=url,
        description=description,
        type=type,
        date=date,
    )
