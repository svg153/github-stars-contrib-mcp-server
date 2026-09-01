"""Common utilities for integration tests."""

import os
import time
from datetime import UTC, datetime

import pytest

from github_stars_contrib_mcp.utils.stars_client import StarsClient


def should_skip_mutations():
    token = os.getenv("STARS_API_TOKEN")
    allow = os.getenv("STARS_E2E_MUTATE", "0") in ("1", "true", "True")
    return not (token and allow)


def skip_if_no_mutations():
    if should_skip_mutations():
        pytest.skip(
            "Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run"
        )


def require_token_or_skip():
    if not os.getenv("STARS_API_TOKEN"):
        pytest.skip("STARS_API_TOKEN not set; skipping integration test")


def get_test_client():
    api_url = os.getenv("STARS_API_URL", "https://api-stars.github.com/")
    contributions_api_url = os.getenv(
        "STARS_CONTRIBUTIONS_API_URL",
        "https://stars.github.com/api/contributions",
    )
    token = os.getenv("STARS_API_TOKEN") or ""
    return StarsClient(
        api_url=api_url,
        contributions_api_url=contributions_api_url,
        token=token,
    )


def generate_unique_url(prefix="github-stars-mcp-e2e"):
    return f"https://example.com/{prefix}/{int(time.time())}"


def get_current_iso_datetime():
    return datetime.now(UTC).isoformat()


def assert_cleanup_success(result, resource_type, resource_id):
    if not result.get("ok"):
        pytest.fail(
            f"Failed to clean up {resource_type} {resource_id}: {result.get('error')}"
        )
