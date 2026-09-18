"""Shared helpers for prompt argument validation and rendering."""

from __future__ import annotations

from datetime import datetime

from ..models import ContributionType

__all__ = [
    "MISSING",
    "STATS_GROUP_BY_VALUES",
    "UNCHANGED",
    "contribution_type_values",
    "parse_optional_date",
    "render_field",
]

MISSING = "[MISSING]"
UNCHANGED = "[UNCHANGED]"

#: ``group_by`` values accepted by ``get_contributions_stats``.
STATS_GROUP_BY_VALUES = ("month", "type", "year")


def contribution_type_values() -> list[str]:
    """Return the canonical ``ContributionType`` values, sorted for stability."""
    return sorted(member.value for member in ContributionType)


def parse_optional_date(value: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp or date, or return ``None`` when absent.

    Raises:
        ValueError: when ``value`` is present but not ISO 8601.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("expected ISO 8601, for example 2026-02-14") from exc


def render_field(label: str, value: object) -> str:
    """Render a ``- label: value`` line, substituting ``[MISSING]`` when empty."""
    return f"- {label}: {value if value not in (None, '') else MISSING}"
