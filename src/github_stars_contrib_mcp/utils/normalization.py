"""Small normalization utilities used across tools.

Keep these helpers minimal and reference them from tools to avoid duplicating
validation/alias logic in multiple places.
"""

from __future__ import annotations


def normalize_platform(value: str) -> tuple[str, bool]:
    """Normalize a platform string to the live API enum values.

    Returns a tuple (normalized_value, was_aliased) where `was_aliased` is True when a
    legacy alias was mapped.

    Accepted aliases:
      - GITHUB -> README
      - WEBSITE -> OTHER
    """
    if value is None:
        return "", False
    upper = str(value).upper()
    alias_map = {
        "GITHUB": "README",
        "WEBSITE": "OTHER",
    }
    mapped = alias_map.get(upper, upper)
    was_aliased = mapped != upper
    return mapped, was_aliased


def normalize_description(desc: str | None) -> str:
    """Ensure description is a non-null string for GraphQL mutations.

    The Stars API accepts an empty string for "no description"; avoid sending
    null to keep behavior consistent across single/bulk mutations.
    """
    return (desc or "").strip()
