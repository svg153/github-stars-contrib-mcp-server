"""Integration tests for profile end-to-end."""

import time

import pytest

from .test_integration_utils import get_test_client, skip_if_no_mutations


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_update_profile_e2e():
    skip_if_no_mutations()

    client = get_test_client()

    # Get current profile data
    user_data = await client.get_user_data()
    assert user_data.get("ok") is True
    logged_user = user_data.get("data", {}).get("loggedUser")
    if not logged_user:
        pytest.skip("Token not valid for reading user data or loggedUser is null; skipping profile update e2e test")
    nominee = logged_user.get("nominee", {})
    original_bio = nominee.get("bio") if nominee else None

    # Update bio to a test value
    test_bio = f"E2E Test Bio {int(time.time())}"
    update_result = await client.update_profile({"bio": test_bio})
    assert update_result.get("ok") is True
    print(f"Updated profile bio to '{test_bio}'")

    # Verify update
    updated_data = await client.get_user_data()
    assert updated_data.get("ok") is True
    updated_nominee = updated_data.get("data", {}).get("loggedUser", {}).get("nominee", {})
    assert updated_nominee.get("bio") == test_bio

    # Revert bio to original
    revert_data = {"bio": original_bio} if original_bio is not None else {}
    if original_bio is None:
        revert_data = {"bio": ""}  # Assuming empty if was None
    revert_result = await client.update_profile(revert_data)
    if not revert_result.get("ok"):
        pytest.fail(f"Failed to revert profile bio: {revert_result.get('error')}")
    print(f"Reverted profile bio to original: '{original_bio}'")
