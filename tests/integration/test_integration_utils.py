"""Common utilities for integration tests."""

import os
import time
from datetime import datetime, timezone

import pytest

from github_stars_contrib_mcp.utils.stars_client import StarsClient


def should_skip_mutations():
    """Check if mutations should be skipped."""
    token = os.getenv("STARS_API_TOKEN")
    allow = os.getenv("STARS_E2E_MUTATE", "0") in ("1", "true", "True")
    return not (token and allow)


def skip_if_no_mutations():
    """Skip test if mutations are not enabled."""
    if should_skip_mutations():
        pytest.skip("Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run")


def get_test_client():
    """Get a StarsClient for testing."""
    api_url = os.getenv("STARS_API_URL", "https://api-stars.github.com/")
    token = os.getenv("STARS_API_TOKEN")
    return StarsClient(api_url=api_url, token=token)


def generate_unique_url(prefix="github-stars-mcp-e2e"):
    """Generate a unique URL for testing."""
    return f"https://example.com/{prefix}/{int(time.time())}"


def get_current_iso_datetime():
    """Get current datetime in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def assert_cleanup_success(result, resource_type, resource_id):
    """Assert that cleanup was successful, fail if not."""
    if not result.get("ok"):
        pytest.fail(f"Failed to clean up {resource_type} {resource_id}: {result.get('error')}")