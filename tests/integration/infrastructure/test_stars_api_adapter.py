import pytest

from github_stars_contrib_mcp.infrastructure.adapters.stars_api_graphql import (
    StarsAPIAdapter,
)
from github_stars_contrib_mcp.utils.models import APIResult


class FakeStarsClientOK:
    async def get_user_data(self):
        return APIResult(True, {"viewer": {"login": "ok-user"}})


class FakeStarsClientFail:
    async def get_user_data(self):
        return APIResult(False, None, "nope")


@pytest.mark.asyncio
async def test_adapter_returns_data_on_success():
    adapter = StarsAPIAdapter(FakeStarsClientOK())  # type: ignore[arg-type]
    data = await adapter.get_user_data()
    assert data["viewer"]["login"] == "ok-user"


@pytest.mark.asyncio
async def test_adapter_raises_on_error():
    adapter = StarsAPIAdapter(FakeStarsClientFail())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="nope"):
        await adapter.get_user_data()
