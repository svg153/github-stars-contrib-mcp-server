import pytest

from github_stars_contrib_mcp.config.settings import settings
from github_stars_contrib_mcp.tools import create_contributions as create_contribs_mod
from github_stars_contrib_mcp.tools import create_link as create_link_mod
from github_stars_contrib_mcp.tools import update_link as update_link_mod


@pytest.mark.asyncio
async def test_create_link_rejects_invalid_url(monkeypatch):
    # Enable validation and force invalid
    monkeypatch.setattr(settings, "validate_urls", True)
    monkeypatch.setattr(settings, "url_validation_timeout_s", 1)

    async def _bad(url, timeout_s=None):
        return (False, "status 404")

    monkeypatch.setattr(create_link_mod, "check_url_head", _bad)

    res = await create_link_mod.create_link_impl("https://example.com/x", "OTHER")
    assert res["success"] is False
    assert "Invalid URL (status 404)" in res["error"]


@pytest.mark.asyncio
async def test_create_link_accepts_valid_url_and_calls_use_case(monkeypatch):
    monkeypatch.setattr(settings, "validate_urls", True)

    async def _ok(url, timeout_s=None):
        return (True, None)

    monkeypatch.setattr(create_link_mod, "check_url_head", _ok)

    called = {}

    class FakeUseCase:
        async def __call__(self, link, platform):
            called["link"] = link
            called["platform"] = platform
            return {"ok": True}

    monkeypatch.setattr(create_link_mod, "CreateLink", lambda *_: FakeUseCase())
    monkeypatch.setattr(create_link_mod, "get_stars_api", lambda: object())

    res = await create_link_mod.create_link_impl("https://example.com/x", "OTHER")
    assert res["success"] is True
    assert called["link"] == "https://example.com/x"
    assert called["platform"] == "OTHER"


@pytest.mark.asyncio
async def test_update_link_rejects_invalid_url(monkeypatch):
    monkeypatch.setattr(settings, "validate_urls", True)

    async def _bad2(url, timeout_s=None):
        return (False, "timeout")

    monkeypatch.setattr(update_link_mod, "check_url_head", _bad2)

    res = await update_link_mod.update_link_impl(
        "id1", {"link": "https://example.com/"}
    )
    assert res["success"] is False
    assert "Invalid URL (timeout) for: https://example.com" in res["error"]


@pytest.mark.asyncio
async def test_update_link_accepts_valid_url_and_strips_trailing_slash(monkeypatch):
    monkeypatch.setattr(settings, "validate_urls", True)

    async def _ok2(url, timeout_s=None):
        return (True, None)

    monkeypatch.setattr(update_link_mod, "check_url_head", _ok2)

    captured = {}

    class FakeUseCase:
        async def __call__(self, link_id, *, link=None, platform=None):
            captured["id"] = link_id
            captured["link"] = link
            captured["platform"] = platform
            return {"ok": True}

    monkeypatch.setattr(update_link_mod, "UpdateLink", lambda *_: FakeUseCase())
    monkeypatch.setattr(update_link_mod, "get_stars_api", lambda: object())

    res = await update_link_mod.update_link_impl(
        "id1", {"link": "https://example.com/"}
    )
    assert res["success"] is True
    assert captured["link"] == "https://example.com"


@pytest.mark.asyncio
async def test_create_contributions_validates_urls(monkeypatch):
    monkeypatch.setattr(settings, "validate_urls", True)

    # Invalid path
    async def _bad3(url, timeout_s=None):
        return (False, "error")

    monkeypatch.setattr(create_contribs_mod, "check_url_head", _bad3)
    res_bad = await create_contribs_mod.create_contributions_impl(
        [
            {
                "title": "t",
                "url": "https://example.com/a",
                "description": None,
                "type": "BLOGPOST",
                "date": "2025-01-01T00:00:00Z",
            }
        ]
    )
    assert res_bad["success"] is False and "Invalid URL (error)" in res_bad["error"]

    # Valid path
    async def _ok3(url, timeout_s=None):
        return (True, None)

    monkeypatch.setattr(create_contribs_mod, "check_url_head", _ok3)

    class FakeUseCase:
        async def __call__(self, items):
            return {"ids": ["1"]}

    monkeypatch.setattr(
        create_contribs_mod, "CreateContributions", lambda *_: FakeUseCase()
    )
    monkeypatch.setattr(create_contribs_mod, "get_stars_api", lambda: object())

    res_ok = await create_contribs_mod.create_contributions_impl(
        [
            {
                "title": "t",
                "url": "https://example.com/a",
                "description": None,
                "type": "BLOGPOST",
                "date": "2025-01-01T00:00:00Z",
            }
        ]
    )
    assert res_ok["success"] is True and res_ok.get("ids") == ["1"]
