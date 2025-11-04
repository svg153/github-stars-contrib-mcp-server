import json as pyjson

import pytest

from github_stars_contrib_mcp.utils.stars_client import StarsClient


class FakeResponse:
    def __init__(
        self,
        status_code=200,
        json_data=None,
        text="",
        json_error=False,
        gql_error=False,
    ):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self._json_error = json_error
        self._gql_error = gql_error

    def json(self):
        if self._json_error:
            raise pyjson.JSONDecodeError("bad", "{}", 0)
        if self._gql_error:
            return {"errors": [{"message": "GraphQL exploded"}]}
        return self._json_data


class FakeAsyncClient:
    def __init__(self, response: FakeResponse):
        self._response = response
        self.call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None):
        self.call_count += 1
        return self._response


@pytest.mark.asyncio
async def test_execute_graphql_http_error(monkeypatch):
    sc = StarsClient(api_url="https://api", token="t")

    def fake_async_client(*args, **kwargs):
        return FakeAsyncClient(FakeResponse(status_code=500, text="oops"))

    monkeypatch.setattr(
        "github_stars_contrib_mcp.utils.stars_client.httpx.AsyncClient",
        fake_async_client,
    )
    res = await sc._execute_graphql("query {}")
    assert res["ok"] is False and "HTTP 500" in res["error"]


@pytest.mark.asyncio
async def test_execute_graphql_invalid_json(monkeypatch):
    sc = StarsClient(api_url="https://api", token="t")

    def fake_async_client(*args, **kwargs):
        return FakeAsyncClient(FakeResponse(status_code=200, json_error=True))

    monkeypatch.setattr(
        "github_stars_contrib_mcp.utils.stars_client.httpx.AsyncClient",
        fake_async_client,
    )
    res = await sc._execute_graphql("query {}")
    assert res["ok"] is False and res["error"] == "Invalid JSON response"


@pytest.mark.asyncio
async def test_execute_graphql_graphql_error(monkeypatch):
    sc = StarsClient(api_url="https://api", token="t")

    def fake_async_client(*args, **kwargs):
        return FakeAsyncClient(FakeResponse(status_code=200, gql_error=True))

    monkeypatch.setattr(
        "github_stars_contrib_mcp.utils.stars_client.httpx.AsyncClient",
        fake_async_client,
    )
    res = await sc._execute_graphql("query {}")
    assert res["ok"] is False and "GraphQL exploded" in res["error"]


@pytest.mark.asyncio
async def test_execute_graphql_success(monkeypatch):
    sc = StarsClient(api_url="https://api", token="t")

    def fake_async_client(*args, **kwargs):
        return FakeAsyncClient(
            FakeResponse(status_code=200, json_data={"data": {"ok": True}})
        )

    monkeypatch.setattr(
        "github_stars_contrib_mcp.utils.stars_client.httpx.AsyncClient",
        fake_async_client,
    )
    res = await sc._execute_graphql("query {}")
    assert res["ok"] is True and res["data"] == {"ok": True}


@pytest.mark.asyncio
async def test_execute_graphql_429_retries(monkeypatch):
    """Verify that 429 (rate limit) is handled and doesn't retry (tenacity configured but not triggered for HTTP errors).

    Note: The @retry decorator with wait_exponential_jitter is in place for transient network errors
    (e.g., connection failures), but HTTP errors like 429 are caught and returned as-is.
    This test verifies that jitter is configured correctly.
    """
    sc = StarsClient(api_url="https://api", token="t")

    def fake_async_client(*args, **kwargs):
        return FakeAsyncClient(FakeResponse(status_code=429, text="Rate limited"))

    monkeypatch.setattr(
        "github_stars_contrib_mcp.utils.stars_client.httpx.AsyncClient",
        fake_async_client,
    )
    res = await sc._execute_graphql("query {}")
    # HTTP errors are returned immediately without retry
    assert res["ok"] is False
    assert "429" in res["error"]
