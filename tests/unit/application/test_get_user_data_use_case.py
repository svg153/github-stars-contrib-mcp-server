import pytest

from github_stars_contrib_mcp.application.use_cases.get_user_data import GetUserData


class FakePort:
    async def get_user_data(self):
        return {"viewer": {"login": "alice"}}


class FailingPort:
    async def get_user_data(self):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_get_user_data_happy_path():
    use_case = GetUserData(FakePort())  # type: ignore[arg-type]
    result = await use_case()
    assert result["viewer"]["login"] == "alice"


@pytest.mark.asyncio
async def test_get_user_data_error_bubbles():
    use_case = GetUserData(FailingPort())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="boom"):
        await use_case()
