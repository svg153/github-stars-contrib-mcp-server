"""Native MCP argument completion for prompt parameters.

MCP 2 exposes a ``completion/complete`` request, so enum-like prompt arguments
are completed through the protocol instead of a bespoke tool. The handler is a
pure function of the prompt name, the argument name and the partial value, which
keeps it cheap for clients that autocomplete on every keystroke.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

from ..shared import mcp
from .validation import STATS_GROUP_BY_VALUES, contribution_type_values

__all__ = [
    "COMPLETION_TARGETS",
    "complete_values",
    "handle_completion",
]

_CONTRIBUTION_TYPE = "type"
_GROUP_BY = "group_by"

#: ``(prompt name, argument name) -> allowed values``.
COMPLETION_TARGETS: Mapping[tuple[str, str], Sequence[str]] = {
    ("contribution_create", _CONTRIBUTION_TYPE): contribution_type_values(),
    ("contribution_update", _CONTRIBUTION_TYPE): contribution_type_values(),
    ("contributions_search", _CONTRIBUTION_TYPE): contribution_type_values(),
    ("contributions_stats", _GROUP_BY): list(STATS_GROUP_BY_VALUES),
}

#: Hard cap on returned values to keep completions small on the wire.
_MAX_VALUES = 100


def complete_values(
    prompt: str,
    argument: str,
    partial: str = "",
    *,
    limit: int = _MAX_VALUES,
) -> list[str]:
    """Return allowed values for an argument, filtered by a case-insensitive prefix.

    Args:
        prompt: Registered prompt name, for example ``contribution_create``.
        argument: Argument name, for example ``type``.
        partial: Text typed so far; an empty string returns every value.
        limit: Maximum number of values to return.

    Returns:
        Matching values in their canonical order, or an empty list when the
        argument is not completable.
    """
    values = COMPLETION_TARGETS.get((prompt, argument))
    if not values:
        return []

    prefix = partial.strip().upper()
    if prefix:
        return [value for value in values if value.upper().startswith(prefix)][:limit]
    return list(values)[:limit]


async def handle_completion(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None = None,  # noqa: ARG001 - protocol signature
) -> Completion | None:
    """Resolve a completion request for prompt arguments.

    Resource template references are ignored, and ``None`` is returned when no
    values are known so the client falls back to its own behaviour.
    """
    if not isinstance(ref, PromptReference):
        return None

    values = complete_values(ref.name, argument.name, argument.value)
    if not values:
        return None

    return Completion(values=values, total=len(values))


@mcp.completion()
async def _registered_completion(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None = None,
) -> Completion | None:
    """Protocol entry point; delegates to :func:`handle_completion`."""
    return await handle_completion(ref, argument, context)
