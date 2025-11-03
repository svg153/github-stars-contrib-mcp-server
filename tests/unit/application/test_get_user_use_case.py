import pytest

from github_stars_contrib_mcp.application.use_cases.get_user import GetUser


class FakePort:
    async def get_user(self):
        return {"loggedUser": {"id": "u1"}}


class FailingPort:
    async def get_user(self):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_get_user_happy_path():
    use_case = GetUser(FakePort())
    data = await use_case()
    assert data["loggedUser"]["id"] == "u1"


@pytest.mark.asyncio
async def test_get_user_error_bubbles():
    use_case = GetUser(FailingPort())
    with pytest.raises(RuntimeError, match="boom"):
        await use_case()
