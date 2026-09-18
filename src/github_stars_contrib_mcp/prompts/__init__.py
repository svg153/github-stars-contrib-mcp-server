"""Prompts and argument completions for the Stars contributions server.

Importing this package registers every prompt and the completion handler on the
shared ``MCPServer`` because the decorators run as import side effects. The
server imports this package once, at startup.
"""

from . import completion as completion
from .creation import ContributionDraft, contribution_create, contribution_create_impl
from .errors import build_error, field_errors_from
from .search import SearchPromptArgs, contributions_search, contributions_search_impl
from .stats import StatsPromptArgs, contributions_stats, contributions_stats_impl
from .summary import contributions_summary, contributions_summary_impl
from .update import (
    ContributionUpdateDraft,
    contribution_update,
    contribution_update_impl,
)
from .validation import (
    MISSING,
    STATS_GROUP_BY_VALUES,
    UNCHANGED,
    contribution_type_values,
    parse_optional_date,
    render_field,
)

__all__ = [
    "MISSING",
    "STATS_GROUP_BY_VALUES",
    "UNCHANGED",
    "ContributionDraft",
    "ContributionUpdateDraft",
    "SearchPromptArgs",
    "StatsPromptArgs",
    "build_error",
    "completion",
    "contribution_create",
    "contribution_create_impl",
    "contribution_type_values",
    "contribution_update",
    "contribution_update_impl",
    "contributions_search",
    "contributions_search_impl",
    "contributions_stats",
    "contributions_stats_impl",
    "contributions_summary",
    "contributions_summary_impl",
    "field_errors_from",
    "parse_optional_date",
    "render_field",
]
