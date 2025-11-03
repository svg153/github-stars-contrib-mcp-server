"""Integration tests for contributions end-to-end."""

import pytest

from .test_integration_utils import (
    assert_cleanup_success,
    generate_unique_url,
    get_current_iso_datetime,
    get_test_client,
    skip_if_no_mutations,
)


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_create_contributions_e2e():
    skip_if_no_mutations()

    client = get_test_client()

    unique_url = generate_unique_url("github-stars-mcp-e2e")
    now_iso = get_current_iso_datetime()
    items = [
        {
            "title": "E2E Test Contribution",
            "url": unique_url,
            "description": "Automated test entry; safe to ignore",
            "type": "BLOGPOST",
            "date": now_iso,
        }
    ]
    result = await client.create_contributions(items)
    assert result.ok is True
    assert isinstance(result.ids, list) and len(result.ids) >= 1

    # Clean up: delete the created contribution
    contrib_id = result.ids[0]
    delete_result = await client.delete_contribution(contrib_id)
    assert_cleanup_success(delete_result, "contribution", contrib_id)
    print(f"Successfully cleaned up contribution {contrib_id}")


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_contribution_full_e2e():
    skip_if_no_mutations()

    client = get_test_client()

    unique_url = generate_unique_url("github-stars-mcp-e2e-contrib")
    now_iso = get_current_iso_datetime()

    # Create contribution
    create_result = await client.create_contribution(
        type="BLOGPOST",
        date=now_iso,
        title="E2E Test Contribution",
        url=unique_url,
        description="Automated test entry; safe to ignore"
    )
    assert create_result.get("ok") is True
    contrib_data = create_result.get("data", {}).get("createContribution", {})
    assert "id" in contrib_data
    contrib_id = contrib_data["id"]
    print(f"Created contribution {contrib_id}")

    # Update contribution
    update_data = {
        "title": "Updated E2E Test Contribution",
        "description": "Updated description"
    }
    update_result = await client.update_contribution(contribution_id=contrib_id, data=update_data)
    assert update_result.get("ok") is True
    updated_contrib_data = update_result.get("data", {}).get("updateContribution", {})
    assert updated_contrib_data.get("title") == "Updated E2E Test Contribution"
    print(f"Updated contribution {contrib_id}")

    # Delete contribution
    delete_result = await client.delete_contribution(contrib_id)
    assert_cleanup_success(delete_result, "contribution", contrib_id)
    print(f"Successfully cleaned up contribution {contrib_id}")
