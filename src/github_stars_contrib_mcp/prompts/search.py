"""Prompt that guides an agent through filtering contributions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ValidationError

from ..models import ContributionType
from ..shared import mcp
from .errors import build_error, field_errors_from
from .validation import contribution_type_values, parse_optional_date

__all__ = ["SearchPromptArgs", "contributions_search", "contributions_search_impl"]


class SearchPromptArgs(BaseModel):
    """Validated filter set for ``search_contributions``."""

    username: str
    type: ContributionType | None = None
    title_contains: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


def contributions_search_impl(
    *,
    username: str | None = None,
    type: str | None = None,  # noqa: A002 - mirrors the MCP tool argument name
    title_contains: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """Validate the filters and render the search instructions."""
    if not username:
        return build_error(
            "contributions_search",
            {"username": "required"},
            hint="Search reads public profile data, so a GitHub username is required.",
        )

    parsed_dates: dict[str, datetime | None] = {}
    for field, raw in (("date_from", date_from), ("date_to", date_to)):
        try:
            parsed_dates[field] = parse_optional_date(raw)
        except ValueError as exc:
            return build_error(
                "contributions_search",
                {field: str(exc)},
                hint="Pass ISO 8601 dates or plain YYYY-MM-DD values.",
            )

    parsed_from = parsed_dates["date_from"]
    parsed_to = parsed_dates["date_to"]

    try:
        args = SearchPromptArgs(
            username=username,
            type=ContributionType(type) if type else None,
            title_contains=title_contains,
            date_from=parsed_from,
            date_to=parsed_to,
        )
    except ValidationError as exc:
        return build_error(
            "contributions_search",
            field_errors_from(exc),
            suggestions={"type": contribution_type_values()},
        )
    except ValueError as exc:
        return build_error(
            "contributions_search",
            {"type": str(exc)},
            suggestions={"type": contribution_type_values()},
            hint="Use one of the suggested ContributionType values.",
        )

    if args.date_from and args.date_to and args.date_to < args.date_from:
        return build_error(
            "contributions_search",
            {"date_to": "must not be earlier than date_from"},
            hint="Swap the bounds or widen the range.",
        )

    filters = [
        f"- username: {args.username}",
        f"- type: {args.type.value if args.type else '[ANY]'}",
        f"- title_contains: {args.title_contains or '[ANY]'}",
        f"- date_from: {args.date_from.isoformat() if args.date_from else '[ANY]'}",
        f"- date_to: {args.date_to.isoformat() if args.date_to else '[ANY]'}",
    ]

    return "\n".join(
        [
            "Search GitHub Stars contributions with the filters below.",
            "",
            "Filters:",
            *filters,
            "",
            "Next steps:",
            "- Call `search_contributions` with a single `args` object containing "
            "username plus only the filters that are not `[ANY]`.",
            "- The tool filters locally, so an over-broad result set is cheap but "
            "still worth narrowing before presenting it.",
            "- Report the match count and the applied filters alongside the results.",
        ]
    )


@mcp.prompt()
def contributions_search(  # noqa: A002 - `type` is the documented MCP argument name
    username: str | None = None,
    type: str | None = None,
    title_contains: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """Build and validate a filter set for the search tool."""
    return contributions_search_impl(
        username=username,
        type=type,
        title_contains=title_contains,
        date_from=date_from,
        date_to=date_to,
    )
