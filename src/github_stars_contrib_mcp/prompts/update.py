"""Prompt that guides an agent through updating an existing contribution.

The current Stars REST API exposes an idempotent ``PUT /{clientId}`` upsert that
requires the *complete* contribution. There is no partial-update mutation, so an
update is a read-modify-write against a stable caller-controlled client ID.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl, ValidationError

from ..models import ContributionType
from ..shared import mcp
from .errors import build_error, field_errors_from
from .validation import (
    UNCHANGED,
    contribution_type_values,
    parse_optional_date,
    render_field,
)

__all__ = [
    "ContributionUpdateDraft",
    "contribution_update",
    "contribution_update_impl",
]


class ContributionUpdateDraft(BaseModel):
    """Fields the caller wants to change; ``None`` means "leave unchanged"."""

    title: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    type: ContributionType | None = None
    date: datetime | None = None


def _coerce_type(value: str | None) -> ContributionType | None:
    if not value:
        return None
    try:
        return ContributionType(value)
    except ValueError as exc:
        raise ValueError(f"unknown contribution type {value!r}") from exc


def contribution_update_impl(
    client_id: str | None = None,
    *,
    title: str | None = None,
    url: str | None = None,
    description: str | None = None,
    type: str | None = None,  # noqa: A002 - mirrors the MCP tool argument name
    date: str | None = None,
) -> str:
    """Validate the requested changes and render the upsert instructions."""
    if not client_id:
        return build_error(
            "contribution_update",
            {"client_id": "required"},
            hint=(
                "Pass the stable REST client ID previously chosen by the caller. "
                "Legacy server-generated contribution IDs are not client IDs."
            ),
        )

    try:
        parsed_date = parse_optional_date(date)
    except ValueError as exc:
        return build_error(
            "contribution_update",
            {"date": str(exc)},
            hint="Pass an ISO 8601 date such as 2026-02-14.",
        )

    try:
        draft = ContributionUpdateDraft(
            title=title,
            url=url,
            description=description,
            type=_coerce_type(type),
            date=parsed_date,
        )
    except ValidationError as exc:
        return build_error(
            "contribution_update",
            field_errors_from(exc),
            suggestions={"type": contribution_type_values()},
        )
    except ValueError as exc:
        return build_error(
            "contribution_update",
            {"type": str(exc)},
            suggestions={"type": contribution_type_values()},
            hint="Use one of the suggested ContributionType values.",
        )

    changes = {
        "title": draft.title,
        "url": str(draft.url) if draft.url else None,
        "description": draft.description,
        "type": draft.type.value if draft.type else None,
        "date": draft.date.isoformat() if draft.date else None,
    }
    changed = [name for name, value in changes.items() if value is not None]

    if not changed:
        return build_error(
            "contribution_update",
            {"changes": "none provided"},
            hint="Provide at least one field to change, or use the summary prompt.",
        )

    lines = [
        f"Update the contribution identified by client ID {client_id!r}.",
        "",
        "Requested changes:",
        *(render_field(name, changes[name]) for name in changed),
    ]

    if len(changed) < len(changes):
        lines.append(f"- (every field not listed above stays {UNCHANGED})")

    lines += [
        "",
        "Next steps:",
        "- The REST profile is an idempotent `PUT /{clientId}` upsert that needs "
        "the complete contribution, so read the current values first.",
        "- Merge the requested changes on top of the current values, keeping any "
        f"field marked {UNCHANGED} exactly as it is.",
        "- Call `upsert_contribution` with `client_id` and the full `data` object "
        "(title, url, type, date, optional description).",
        f"- If a field marked {UNCHANGED} looks wrong, ask the user before "
        "overwriting it.",
    ]
    return "\n".join(lines)


@mcp.prompt()
def contribution_update(  # noqa: A002 - `type` is the documented MCP argument name
    client_id: str,
    title: str | None = None,
    url: str | None = None,
    description: str | None = None,
    type: str | None = None,
    date: str | None = None,
) -> str:
    """Draft a full-payload upsert for an existing contribution."""
    return contribution_update_impl(
        client_id,
        title=title,
        url=url,
        description=description,
        type=type,
        date=date,
    )
