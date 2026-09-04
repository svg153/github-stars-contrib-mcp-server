"""Conservative eligibility rules for GitHub-derived contribution candidates."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from github_stars_contrib_mcp.models import ContributionType


class GitHubEligibilityReason(StrEnum):
    OWNED_RELEASE = "owned_release"
    OWNED_REPOSITORY_EXPLICIT = "owned_repository_explicit"
    CONFIGURED_NOTABLE_ACTIVITY = "configured_notable_activity"
    DRAFT_RELEASE = "draft_release"
    FORK = "fork"
    ARCHIVED = "archived"
    NOT_OWNER = "not_owner"
    NOT_AUTHOR = "not_author"
    ROUTINE_ACTIVITY = "routine_activity"
    NOT_EXPLICITLY_CONFIGURED = "not_explicitly_configured"
    UNKNOWN_ACTIVITY = "unknown_activity"


class GitHubEligibilityDecision(BaseModel):
    """Explainable default-deny result for one GitHub item."""

    model_config = ConfigDict(extra="forbid")

    eligible: bool
    reason_code: GitHubEligibilityReason
    contribution_type: ContributionType | None = None
    confidence: float = 0.0


_ROUTINE_KINDS = frozenset(
    {
        "commit",
        "push",
        "star",
        "watch",
        "fork_event",
        "branch",
        "tag",
    }
)
_NOTABLE_KINDS = frozenset({"pull_request", "issue", "discussion", "community"})


def _login(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, dict):
        login = value.get("login")
        if isinstance(login, str):
            return login
    return ""


def _repository_owner(payload: dict[str, Any]) -> str:
    repository = payload.get("repository")
    if isinstance(repository, dict):
        owner = _login(repository, "owner")
        if owner:
            return owner
        full_name = repository.get("full_name")
        if isinstance(full_name, str) and "/" in full_name:
            return full_name.split("/", 1)[0]
    owner = _login(payload, "owner")
    if owner:
        return owner
    full_name = payload.get("full_name")
    if isinstance(full_name, str) and "/" in full_name:
        return full_name.split("/", 1)[0]
    return ""


def evaluate_github_item(
    kind: str,
    payload: dict[str, Any],
    *,
    trusted_username: str,
    explicitly_configured: bool = False,
) -> GitHubEligibilityDecision:
    """Evaluate one GitHub object without inferring significance from routine activity."""

    normalized_kind = kind.strip().lower()
    trusted = trusted_username.strip().lower()

    if normalized_kind in _ROUTINE_KINDS:
        return GitHubEligibilityDecision(
            eligible=False,
            reason_code=GitHubEligibilityReason.ROUTINE_ACTIVITY,
        )

    if normalized_kind == "release":
        if bool(payload.get("draft")):
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.DRAFT_RELEASE,
            )
        if _repository_owner(payload).lower() != trusted:
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.NOT_OWNER,
            )
        return GitHubEligibilityDecision(
            eligible=True,
            reason_code=GitHubEligibilityReason.OWNED_RELEASE,
            contribution_type=ContributionType.OPEN_SOURCE_PROJECT,
            confidence=0.95,
        )

    if normalized_kind == "repository":
        if bool(payload.get("fork")):
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.FORK,
            )
        if bool(payload.get("archived")):
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.ARCHIVED,
            )
        if _repository_owner(payload).lower() != trusted:
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.NOT_OWNER,
            )
        if not explicitly_configured:
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.NOT_EXPLICITLY_CONFIGURED,
            )
        return GitHubEligibilityDecision(
            eligible=True,
            reason_code=GitHubEligibilityReason.OWNED_REPOSITORY_EXPLICIT,
            contribution_type=ContributionType.OPEN_SOURCE_PROJECT,
            confidence=0.85,
        )

    if normalized_kind in _NOTABLE_KINDS:
        if _login(payload, "user").lower() != trusted:
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.NOT_AUTHOR,
            )
        if not explicitly_configured:
            return GitHubEligibilityDecision(
                eligible=False,
                reason_code=GitHubEligibilityReason.NOT_EXPLICITLY_CONFIGURED,
            )
        return GitHubEligibilityDecision(
            eligible=True,
            reason_code=GitHubEligibilityReason.CONFIGURED_NOTABLE_ACTIVITY,
            contribution_type=ContributionType.OTHER,
            confidence=0.75,
        )

    return GitHubEligibilityDecision(
        eligible=False,
        reason_code=GitHubEligibilityReason.UNKNOWN_ACTIVITY,
    )
