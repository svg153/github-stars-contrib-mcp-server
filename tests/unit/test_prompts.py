"""Unit tests for the contributions prompts."""

import asyncio
import json

import pytest

from github_stars_contrib_mcp import prompts
from github_stars_contrib_mcp.shared import mcp


def _error_payload(text: str) -> dict:
    """Parse the JSON body of an ``[ERROR]`` prompt response."""
    assert text.startswith("[ERROR] ")
    _, body = text.split("\n", 1)
    return json.loads(body)


def test_prompts_are_registered():
    names = {prompt.name for prompt in asyncio.run(mcp.list_prompts())}
    assert {
        "contribution_create",
        "contribution_update",
        "contributions_summary",
        "contributions_search",
        "contributions_stats",
    } <= names


class TestContributionCreate:
    def test_complete_draft_lists_no_missing_fields(self):
        result = prompts.contribution_create(
            title="Intro to MCP",
            url="https://example.com/talk",
            type="SPEAKING",
            date="2026-02-14",
        )
        assert "All required fields are present." in result
        assert "create_contribution" in result
        assert "upsert_contribution" in result

    def test_partial_draft_reports_missing_fields(self):
        result = prompts.contribution_create(title="Intro to MCP")
        assert "Missing required fields: url, type, date." in result
        assert "[MISSING]" in result

    def test_unknown_type_returns_suggestions(self):
        result = prompts.contribution_create(type="TALK")
        payload = _error_payload(result)
        assert payload["prompt"] == "contribution_create"
        assert "type" in payload["field_errors"]
        assert "SPEAKING" in payload["suggestions"]["type"]

    def test_invalid_date_is_rejected(self):
        result = prompts.contribution_create(date="14/02/2026")
        payload = _error_payload(result)
        assert "date" in payload["field_errors"]

    def test_invalid_url_is_rejected(self):
        result = prompts.contribution_create(url="not-a-url")
        payload = _error_payload(result)
        assert "url" in payload["field_errors"]


class TestContributionUpdate:
    def test_requires_client_id(self):
        payload = _error_payload(prompts.contribution_update(None, title="New"))
        assert payload["field_errors"]["client_id"] == "required"
        assert "client ID" in payload["hint"]

    def test_requires_at_least_one_change(self):
        payload = _error_payload(prompts.contribution_update("post:1"))
        assert payload["field_errors"]["changes"] == "none provided"

    def test_partial_update_marks_unchanged_fields(self):
        result = prompts.contribution_update("post:1", title="Renamed")
        assert "Renamed" in result
        assert "[UNCHANGED]" in result
        assert "upsert_contribution" in result

    def test_unknown_type_returns_suggestions(self):
        payload = _error_payload(prompts.contribution_update("post:1", type="TALK"))
        assert "SPEAKING" in payload["suggestions"]["type"]

    def test_invalid_date_is_rejected(self):
        payload = _error_payload(
            prompts.contribution_update("post:1", date="not-a-date")
        )
        assert "date" in payload["field_errors"]


class TestContributionsSummary:
    def test_default_page(self):
        result = prompts.contributions_summary()
        assert "Start at page 1." in result
        assert "list_contributions" in result

    def test_rejects_non_positive_page(self):
        payload = _error_payload(prompts.contributions_summary(page=0))
        assert payload["field_errors"]["page"] == "must be >= 1"


class TestContributionsSearch:
    def test_requires_username(self):
        payload = _error_payload(prompts.contributions_search(type="BLOGPOST"))
        assert payload["field_errors"]["username"] == "required"

    def test_lists_applied_filters(self):
        result = prompts.contributions_search(
            username="alice", type="BLOGPOST", title_contains="mcp"
        )
        assert "- username: alice" in result
        assert "- type: BLOGPOST" in result
        assert "- title_contains: mcp" in result
        assert "search_contributions" in result

    def test_unknown_type_returns_suggestions(self):
        payload = _error_payload(
            prompts.contributions_search(username="alice", type="TALK")
        )
        assert "BLOGPOST" in payload["suggestions"]["type"]

    def test_invalid_date_is_rejected(self):
        payload = _error_payload(
            prompts.contributions_search(username="alice", date_from="oops")
        )
        assert "date_from" in payload["field_errors"]

    def test_inverted_range_is_rejected(self):
        payload = _error_payload(
            prompts.contributions_search(
                username="alice",
                date_from="2026-02-01",
                date_to="2026-01-01",
            )
        )
        assert "date_to" in payload["field_errors"]


class TestContributionsStats:
    def test_requires_username(self):
        payload = _error_payload(prompts.contributions_stats(group_by="type"))
        assert payload["field_errors"]["username"] == "required"

    def test_flat_totals_without_grouping(self):
        result = prompts.contributions_stats(username="alice")
        assert "- group_by: [NONE]" in result
        assert "get_contributions_stats" in result

    def test_supported_grouping(self):
        result = prompts.contributions_stats(username="alice", group_by="year")
        assert "- group_by: year" in result

    def test_unsupported_grouping_returns_suggestions(self):
        payload = _error_payload(
            prompts.contributions_stats(username="alice", group_by="quarter")
        )
        assert payload["field_errors"]["group_by"] == "unsupported value"
        assert payload["suggestions"]["group_by"] == ["month", "type", "year"]

    def test_include_ui_is_reported(self):
        result = prompts.contributions_stats(username="alice", include_ui=True)
        assert "- include_ui: True" in result


@pytest.mark.parametrize(
    "text",
    [
        prompts.contribution_create(type="nope"),
        prompts.contribution_update("post:1", type="nope"),
        prompts.contributions_search(username="alice", type="nope"),
    ],
)
def test_error_responses_are_valid_json(text):
    payload = _error_payload(text)
    assert set(payload) <= {"prompt", "field_errors", "suggestions", "hint"}
    assert payload["field_errors"]
