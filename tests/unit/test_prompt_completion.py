"""Unit tests for native prompt argument completion."""

import pytest
from mcp.types import (
    CompletionArgument,
    PromptReference,
    ResourceTemplateReference,
)

from github_stars_contrib_mcp.prompts import completion as prompt_completion
from github_stars_contrib_mcp.prompts.completion import (
    COMPLETION_TARGETS,
    complete_values,
    handle_completion,
)


class TestCompleteValues:
    def test_empty_partial_returns_every_value(self):
        values = complete_values("contribution_create", "type")
        assert "SPEAKING" in values
        assert "OTHER" in values

    def test_prefix_filter_is_case_insensitive(self):
        values = complete_values("contribution_create", "type", "sp")
        assert values == ["SPEAKING"]

    def test_unknown_prompt_returns_empty(self):
        assert complete_values("nope", "type") == []

    def test_unknown_argument_returns_empty(self):
        assert complete_values("contribution_create", "title") == []

    def test_group_by_values(self):
        values = complete_values("contributions_stats", "group_by", "y")
        assert values == ["year"]

    def test_respects_limit(self):
        values = complete_values("contribution_create", "type", "", limit=2)
        assert len(values) == 2

    def test_all_targets_resolve(self):
        for (prompt, argument), expected in COMPLETION_TARGETS.items():
            assert complete_values(prompt, argument) == list(expected)


class TestHandleCompletion:
    async def test_prompt_reference_returns_completion(self):
        result = await handle_completion(
            PromptReference(name="contributions_stats"),
            CompletionArgument(name="group_by", value="t"),
        )
        assert result is not None
        assert result.values == ["type"]

    async def test_unknown_argument_returns_none(self):
        result = await handle_completion(
            PromptReference(name="contribution_create"),
            CompletionArgument(name="unknown", value=""),
        )
        assert result is None

    async def test_no_match_returns_none(self):
        result = await handle_completion(
            PromptReference(name="contribution_create"),
            CompletionArgument(name="type", value="zzz"),
        )
        assert result is None

    async def test_resource_template_reference_is_ignored(self):
        result = await handle_completion(
            ResourceTemplateReference(uri="metrics://{name}"),
            CompletionArgument(name="name", value=""),
        )
        assert result is None

    async def test_context_argument_is_accepted(self):
        result = await handle_completion(
            PromptReference(name="contribution_create"),
            CompletionArgument(name="type", value=""),
            None,
        )
        assert result is not None
        assert result.total == len(result.values)

    async def test_registered_handler_delegates(self):
        result = await prompt_completion._registered_completion(
            PromptReference(name="contribution_update"),
            CompletionArgument(name="type", value="blog"),
        )
        assert result is not None
        assert result.values == ["BLOGPOST"]


@pytest.mark.parametrize("prompt_name", ["contribution_create", "contribution_update"])
def test_contribution_type_targets_share_values(prompt_name):
    assert complete_values(prompt_name, "type") == list(
        COMPLETION_TARGETS[("contribution_create", "type")]
    )
