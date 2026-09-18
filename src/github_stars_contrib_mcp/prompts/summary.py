"""Prompt that guides an agent through summarising the Stars profile."""

from __future__ import annotations

from ..shared import mcp
from .errors import build_error

__all__ = ["contributions_summary", "contributions_summary_impl"]


def contributions_summary_impl(page: int = 1) -> str:
    """Validate the page number and render the listing instructions."""
    if page < 1:
        return build_error(
            "contributions_summary",
            {"page": "must be >= 1"},
            hint="Pages are 1-based; start at page 1.",
        )

    return "\n".join(
        [
            "Summarise my GitHub Stars contributions.",
            "",
            f"Start at page {page}.",
            "",
            "Next steps:",
            "- Call `list_contributions` with `page` to read the authenticated "
            "profile through the REST Contributions API.",
            "- Continue with the next page while the response still returns "
            "items, then stop.",
            "- Group the result by type and call out totals, the date range and "
            "any obvious gaps.",
            "- Use `get_contributions_stats` when aggregate numbers are needed "
            "instead of a narrative summary.",
            "- Use `search_contributions` instead when you only need a filtered "
            "subset.",
        ]
    )


@mcp.prompt(title="Summarize my contributions")
def contributions_summary(page: int = 1) -> str:
    """Plan a paginated read of the authenticated contributions profile."""
    return contributions_summary_impl(page=page)
