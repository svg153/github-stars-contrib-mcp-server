import pytest

from github_stars_contrib_mcp.tools.profile import get_user_data_tool


class FakePort:
    async def get_user_data(self):
        return {"me": {"id": "1"}}


@pytest.mark.asyncio
async def test_tool_run_uses_di_and_returns_data(monkeypatch):
    monkeypatch.setattr(get_user_data_tool, "get_stars_api", FakePort)
    data = await get_user_data_tool.run()
    assert data == {"me": {"id": "1"}}
