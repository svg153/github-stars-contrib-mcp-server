"""Conservative GitHub eligibility rules avoid noisy Stars candidates."""

from github_stars_contrib_mcp.application.discovery.github_eligibility import (
    GitHubEligibilityReason,
    evaluate_github_item,
)
from github_stars_contrib_mcp.models import ContributionType


def _repo(**overrides):
    payload = {
        "id": 1,
        "full_name": "alice/project",
        "owner": {"login": "alice"},
        "fork": False,
        "archived": False,
    }
    payload.update(overrides)
    return payload


def test_owned_release_is_eligible() -> None:
    decision = evaluate_github_item(
        "release",
        {
            "draft": False,
            "repository": _repo(),
        },
        trusted_username="alice",
    )
    assert decision.eligible is True
    assert decision.reason_code is GitHubEligibilityReason.OWNED_RELEASE
    assert decision.contribution_type is ContributionType.OPEN_SOURCE_PROJECT


def test_draft_release_and_foreign_release_are_rejected() -> None:
    draft = evaluate_github_item(
        "release",
        {"draft": True, "repository": _repo()},
        trusted_username="alice",
    )
    foreign = evaluate_github_item(
        "release",
        {"draft": False, "repository": _repo(owner={"login": "bob"})},
        trusted_username="alice",
    )
    assert draft.reason_code is GitHubEligibilityReason.DRAFT_RELEASE
    assert foreign.reason_code is GitHubEligibilityReason.NOT_OWNER


def test_routine_activity_is_always_rejected() -> None:
    for kind in ("commit", "push", "star", "watch", "fork_event", "branch", "tag"):
        decision = evaluate_github_item(kind, {}, trusted_username="alice")
        assert decision.eligible is False
        assert decision.reason_code is GitHubEligibilityReason.ROUTINE_ACTIVITY


def test_repository_requires_explicit_opt_in() -> None:
    default = evaluate_github_item(
        "repository", _repo(), trusted_username="alice"
    )
    explicit = evaluate_github_item(
        "repository",
        _repo(),
        trusted_username="alice",
        explicitly_configured=True,
    )
    assert default.reason_code is GitHubEligibilityReason.NOT_EXPLICITLY_CONFIGURED
    assert explicit.eligible is True
    assert explicit.reason_code is GitHubEligibilityReason.OWNED_REPOSITORY_EXPLICIT


def test_fork_archived_and_foreign_repositories_are_rejected() -> None:
    assert (
        evaluate_github_item(
            "repository",
            _repo(fork=True),
            trusted_username="alice",
            explicitly_configured=True,
        ).reason_code
        is GitHubEligibilityReason.FORK
    )
    assert (
        evaluate_github_item(
            "repository",
            _repo(archived=True),
            trusted_username="alice",
            explicitly_configured=True,
        ).reason_code
        is GitHubEligibilityReason.ARCHIVED
    )
    assert (
        evaluate_github_item(
            "repository",
            _repo(owner={"login": "bob"}),
            trusted_username="alice",
            explicitly_configured=True,
        ).reason_code
        is GitHubEligibilityReason.NOT_OWNER
    )


def test_notable_activity_requires_explicit_configuration_and_authorship() -> None:
    not_explicit = evaluate_github_item(
        "pull_request",
        {"user": {"login": "alice"}},
        trusted_username="alice",
    )
    foreign = evaluate_github_item(
        "pull_request",
        {"user": {"login": "bob"}},
        trusted_username="alice",
        explicitly_configured=True,
    )
    accepted = evaluate_github_item(
        "pull_request",
        {"user": {"login": "alice"}},
        trusted_username="alice",
        explicitly_configured=True,
    )
    assert (
        not_explicit.reason_code
        is GitHubEligibilityReason.NOT_EXPLICITLY_CONFIGURED
    )
    assert foreign.reason_code is GitHubEligibilityReason.NOT_AUTHOR
    assert accepted.eligible is True
    assert accepted.reason_code is GitHubEligibilityReason.CONFIGURED_NOTABLE_ACTIVITY


def test_unknown_activity_is_default_denied() -> None:
    decision = evaluate_github_item("mystery", {}, trusted_username="alice")
    assert decision.eligible is False
    assert decision.reason_code is GitHubEligibilityReason.UNKNOWN_ACTIVITY
