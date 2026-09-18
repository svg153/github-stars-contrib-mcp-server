"""Structured error payloads for prompt argument validation.

Prompt handlers return plain text to the model, so validation failures are
rendered as a stable ``[ERROR]`` prefix followed by a machine-readable JSON
body. Keeping the shape stable lets agents branch on ``field_errors`` and
``suggestions`` instead of parsing prose.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping

from pydantic import ValidationError

__all__ = ["build_error", "field_errors_from"]


def field_errors_from(exc: ValidationError) -> dict[str, str]:
    """Flatten a pydantic ``ValidationError`` into ``{field: message}`` pairs.

    Nested locations are joined with dots (``data.type``) and missing locations
    fall back to ``input`` so the payload always has a key.
    """
    errors: dict[str, str] = {}
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ())) or "input"
        errors[location] = str(error.get("msg", "invalid value"))
    return errors


def build_error(
    prompt: str,
    field_errors: Mapping[str, str],
    *,
    suggestions: Mapping[str, Iterable[str]] | None = None,
    hint: str | None = None,
) -> str:
    """Render a prompt validation failure as ``[ERROR]`` plus a JSON body.

    Args:
        prompt: Name of the prompt that rejected the arguments.
        field_errors: Mapping of argument name to a short human-readable reason.
        suggestions: Optional allowed values per argument. Empty iterables are
            dropped so the payload stays minimal.
        hint: Optional next step the model should take.

    Returns:
        Text with a first line of ``[ERROR] <prompt>`` and a JSON object body.
    """
    payload: dict[str, object] = {
        "prompt": prompt,
        "field_errors": {str(key): str(value) for key, value in field_errors.items()},
    }

    if suggestions:
        cleaned = {
            str(key): sorted({str(item) for item in values})
            for key, values in suggestions.items()
            if values
        }
        if cleaned:
            payload["suggestions"] = cleaned

    if hint:
        payload["hint"] = hint

    body = json.dumps(payload, indent=2, sort_keys=True)
    return f"[ERROR] {prompt}\n{body}"
