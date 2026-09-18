"""Prompt that guides an agent through contribution statistics."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from ..shared import mcp
from .errors import build_error, field_errors_from
from .validation import STATS_GROUP_BY_VALUES

__all__ = ["StatsPromptArgs", "contributions_stats", "contributions_stats_impl"]


class StatsPromptArgs(BaseModel):
    """Validated arguments for ``get_contributions_stats``."""

    username: str
    group_by: str | None = None
    include_ui: bool = False


def contributions_stats_impl(
    *,
    username: str | None = None,
    group_by: str | None = None,
    include_ui: bool = False,
) -> str:
    """Validate the arguments and render the statistics instructions."""
    if not username:
        return build_error(
            "contributions_stats",
            {"username": "required"},
            hint="Statistics are computed from a public profile, so a username is required.",
        )

    try:
        args = StatsPromptArgs(
            username=username, group_by=group_by, include_ui=include_ui
        )
    except ValidationError as exc:
        return build_error("contributions_stats", field_errors_from(exc))

    if args.group_by is not None and args.group_by not in STATS_GROUP_BY_VALUES:
        return build_error(
            "contributions_stats",
            {"group_by": "unsupported value"},
            suggestions={"group_by": list(STATS_GROUP_BY_VALUES)},
            hint="Omit group_by for flat totals, or pick a supported grouping.",
        )

    return "\n".join(
        [
            "Compute statistics for my GitHub Stars contributions.",
            "",
            "Arguments:",
            f"- username: {args.username}",
            f"- group_by: {args.group_by or '[NONE]'}",
            f"- include_ui: {args.include_ui}",
            "",
            "Next steps:",
            "- Call `get_contributions_stats` with a single `args` object "
            "containing username and, when present, group_by and include_ui.",
            "- Supported groupings are "
            + ", ".join(STATS_GROUP_BY_VALUES)
            + "; omit `group_by` for flat totals by type.",
            "- Set `include_ui` only when a rendered chart is useful; it returns "
            "an embedded MCP Apps resource instead of plain JSON.",
            "- Present the headline numbers first and keep the detail per group "
            "available but secondary.",
        ]
    )


@mcp.prompt()
def contributions_stats(
    username: str | None = None,
    group_by: str | None = None,
    include_ui: bool = False,
) -> str:
    """Build and validate the arguments for the statistics tool."""
    return contributions_stats_impl(
        username=username,
        group_by=group_by,
        include_ui=include_ui,
    )
