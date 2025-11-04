import httpx
import pytest

from github_stars_contrib_mcp.config.settings import settings
from github_stars_contrib_mcp.utils import url_check as uc


@pytest.fixture(autouse=True)
def clear_cache():
    # Reset cache before each test
    uc._cache.clear()


@pytest.mark.asyncio
async def test_head_success(monkeypatch):
    calls = {"n": 0}

    class DummyResp:
        def __init__(self, status_code):
            self.status_code = status_code

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url):
            calls["n"] += 1
            return DummyResp(200)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: DummyClient())
    monkeypatch.setattr(settings, "url_validation_ttl_s", 60)
    ok, reason = await uc.check_url_head("https://example.com")
    assert ok is True
    assert reason is None
    # Cached
    ok2, reason2 = await uc.check_url_head("https://example.com")
    assert ok2 is True and reason2 is None
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_head_4xx(monkeypatch):
    class DummyResp:
        def __init__(self, status_code):
            self.status_code = status_code

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url):
            return DummyResp(404)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: DummyClient())
    monkeypatch.setattr(settings, "url_validation_ttl_s", 0)
    ok, reason = await uc.check_url_head("https://example.com/missing")
    assert ok is False and reason == "status 404"


@pytest.mark.asyncio
async def test_head_timeout(monkeypatch):
    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: DummyClient())
    ok, reason = await uc.check_url_head("https://slow.example.com")
    assert ok is False and reason == "timeout"


@pytest.mark.asyncio
async def test_head_generic_error(monkeypatch):
    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url):
            raise RuntimeError("boom")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: DummyClient())
    ok, reason = await uc.check_url_head("https://err.example.com")
    assert ok is False and reason == "error"
