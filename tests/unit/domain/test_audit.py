"""Historical audit domain model tests."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from github_stars_contrib_mcp.domain.audit import AuditRequest
from github_stars_contrib_mcp.domain.discovery import SourceType
from github_stars_contrib_mcp.models import ContributionType


def test_audit_request_normalizes_filters_and_timezones() -> None:
    request = AuditRequest(
        start=datetime(2026, 1, 1),
        end=datetime(2026, 2, 1, tzinfo=UTC),
        source_ids=("b", "a", "a", ""),
        source_types=(SourceType.YOUTUBE, SourceType.GITHUB, SourceType.YOUTUBE),
        contribution_types=(
            ContributionType.SPEAKING,
            ContributionType.BLOGPOST,
            ContributionType.SPEAKING,
        ),
    )

    assert request.start.tzinfo is UTC
    assert request.source_ids == ("a", "b")
    assert request.source_types == (SourceType.GITHUB, SourceType.YOUTUBE)
    assert request.contribution_types == (
        ContributionType.BLOGPOST,
        ContributionType.SPEAKING,
    )
    assert request.read_only is True


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
        (
            datetime(2026, 2, 1, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
    ],
)
def test_audit_request_rejects_empty_or_reversed_window(start, end) -> None:
    with pytest.raises(ValidationError, match="audit start must be before end"):
        AuditRequest(start=start, end=end)
