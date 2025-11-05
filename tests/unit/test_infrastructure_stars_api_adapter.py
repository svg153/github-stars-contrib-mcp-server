import pytest

from github_stars_contrib_mcp.infrastructure.adapters.stars_api_graphql import (
    StarsAPIAdapter,
)
from github_stars_contrib_mcp.utils.models import APIResult


class FakeClient:
    def __init__(self, results):
        # queue of (method_name, APIResult)
        self._results = results

    async def get_user_data(self):
        return self._results.get("get_user_data")

    async def get_user(self):
        return self._results.get("get_user")

    async def get_stars(self, username: str):
        return self._results.get("get_stars")

    async def create_contribution(self, **kwargs):
        return self._results.get("create_contribution")

    async def create_contributions(self, items):
        return self._results.get("create_contributions")

    async def update_contribution(self, contribution_id, data):
        return self._results.get("update_contribution")

    async def delete_contribution(self, contribution_id):
        return self._results.get("delete_contribution")

    async def create_link(self, link, platform):
        return self._results.get("create_link")

    async def update_link(self, link_id, link, platform):
        return self._results.get("update_link")

    async def delete_link(self, link_id):
        return self._results.get("delete_link")

    async def update_profile(self, data):
        return self._results.get("update_profile")


@pytest.mark.asyncio
async def test_adapter_success_paths():
    results = {
        "get_user_data": APIResult(True, {"user": {"id": "u"}}),
        "get_user": APIResult(True, {"me": {"id": "me"}}),
        "get_stars": APIResult(True, {"publicProfile": {"username": "x"}}),
        "create_contribution": APIResult(True, {"createContribution": {"id": "c1"}}),
        "create_contributions": APIResult(
            True, {"createContributions": [{"id": "c1"}, {"id": "c2"}]}
        ),
        "update_contribution": APIResult(True, {"updateContribution": {"id": "c1"}}),
        "delete_contribution": APIResult(True, {"deleteContribution": {"id": "c1"}}),
        "create_link": APIResult(True, {"createLink": {"id": "l1"}}),
        "update_link": APIResult(True, {"updateLink": {"id": "l1"}}),
        "delete_link": APIResult(True, {"deleteLink": {"id": "l1"}}),
        "update_profile": APIResult(True, {"updateProfile": {"id": "me"}}),
    }
    adapter = StarsAPIAdapter(FakeClient(results))

    assert (await adapter.get_user_data())["user"]["id"] == "u"
    assert (await adapter.get_user())["me"]["id"] == "me"
    assert (await adapter.get_stars("who"))["publicProfile"]["username"] == "x"
    assert (
        await adapter.create_contribution(
            type="T", date="D", title="t", url="u", description=""
        )
    )["createContribution"]["id"] == "c1"
    assert (await adapter.create_contributions([{}]))["createContributions"][0][
        "id"
    ] == "c1"
    assert (await adapter.update_contribution("c1", {}))["updateContribution"][
        "id"
    ] == "c1"
    assert (await adapter.delete_contribution("c1"))["deleteContribution"]["id"] == "c1"
    assert (await adapter.create_link("u", "OTHER"))["createLink"]["id"] == "l1"
    assert (await adapter.update_link("l1", "u", "OTHER"))["updateLink"]["id"] == "l1"
    assert (await adapter.delete_link("l1"))["deleteLink"]["id"] == "l1"
    assert (await adapter.update_profile({}))["updateProfile"]["id"] == "me"


@pytest.mark.asyncio
async def test_adapter_error_paths_raise():
    # Exercise a representative subset; all methods share the same error pattern
    failing = APIResult(False, None, "boom")
    adapter = StarsAPIAdapter(
        FakeClient({
            "get_user_data": failing,
            "create_link": failing,
            "update_profile": failing,
        })
    )
    with pytest.raises(RuntimeError):
        await adapter.get_user_data()
    with pytest.raises(RuntimeError):
        await adapter.create_link("u", "OTHER")
    with pytest.raises(RuntimeError):
        await adapter.update_profile({})
