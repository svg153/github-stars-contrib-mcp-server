import pytest

from github_stars_contrib_mcp.application.use_cases.get_stars import GetStars


class FakePort:
    async def get_stars(self, username: str):
        return {"publicProfile": {"username": username}}


@pytest.mark.asyncio
async def test_get_stars_happy_path():
    use_case = GetStars(FakePort())
    data = await use_case("alice")
    assert data["publicProfile"]["username"] == "alice"


@pytest.mark.asyncio
async def test_get_stars_validates_username():
    use_case = GetStars(FakePort())
    with pytest.raises(ValueError):
        await use_case("")
