"""Integration tests for links end-to-end."""

import pytest

from .test_integration_utils import (
    assert_cleanup_success,
    generate_unique_url,
    get_test_client,
    skip_if_no_mutations,
)


@pytest.mark.asyncio
@pytest.mark.client
async def test_integration_links_e2e():
    skip_if_no_mutations()

    client = get_test_client()

    unique_url = generate_unique_url("github-stars-mcp-e2e-link")

    # Create link (use an allowed PlatformType value, e.g., OTHER)
    create_result = await client.create_link(link=unique_url, platform="OTHER")
    assert create_result.get("ok") is True
    link_data = create_result.get("data", {}).get("createLink", {})
    assert "id" in link_data
    link_id = link_data["id"]
    print(f"Created link {link_id}")

    # Update link
    updated_url = unique_url + "-updated"
    update_result = await client.update_link(
        link_id=link_id, link=updated_url, platform="OTHER"
    )
    assert update_result.get("ok") is True
    updated_link_data = update_result.get("data", {}).get("updateLink", {})
    assert updated_link_data.get("link") == updated_url
    print(f"Updated link {link_id}")

    # Delete link
    delete_result = await client.delete_link(link_id)
    assert_cleanup_success(delete_result, "link", link_id)
    print(f"Successfully cleaned up link {link_id}")
