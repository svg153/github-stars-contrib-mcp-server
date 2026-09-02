from __future__ import annotations

import httpx
import pytest

from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    FetchOutcome,
    FetchSecurityClassification,
    SafeFetchRequest,
)
from github_stars_contrib_mcp.infrastructure.http.safe_fetch import SafeHTTPFetcher


async def _resolver(hostname: str) -> list[str]:
    mapping = {
        "public.example": ["93.184.216.34"],
        "other.example": ["1.1.1.1"],
        "private.example": ["10.0.0.8"],
    }
    return mapping[hostname]


@pytest.mark.asyncio
async def test_private_target_is_blocked_before_transport() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="unexpected")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SafeHTTPFetcher(resolver=_resolver, client=client).fetch(
            SafeFetchRequest(url="http://private.example/admin")
        )

    assert result.outcome is FetchOutcome.BLOCKED
    assert result.security is FetchSecurityClassification.BLOCKED_UNSAFE_TARGET
    assert result.error_code == "unsafe_address"
    assert calls == 0


@pytest.mark.asyncio
async def test_redirect_target_is_revalidated_before_following() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1/latest/meta-data"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SafeHTTPFetcher(resolver=_resolver, client=client).fetch(
            SafeFetchRequest(url="https://public.example/start")
        )

    assert result.outcome is FetchOutcome.BLOCKED
    assert result.error_code == "unsafe_address"
    assert result.redirect_count == 1
    assert calls == ["https://public.example/start"]


@pytest.mark.asyncio
async def test_oversize_and_media_type_limits_are_explicit() -> None:
    async def oversize(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain"},
            content=b"x" * 32,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(oversize)) as client:
        result = await SafeHTTPFetcher(resolver=_resolver, client=client).fetch(
            SafeFetchRequest(url="https://public.example/big", max_bytes=10)
        )
    assert result.outcome is FetchOutcome.TOO_LARGE
    assert result.truncated is True
    assert result.text is None

    async def image(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "image/png"},
            content=b"png",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(image)) as client:
        result = await SafeHTTPFetcher(resolver=_resolver, client=client).fetch(
            SafeFetchRequest(url="https://public.example/image")
        )
    assert result.outcome is FetchOutcome.UNSUPPORTED_MEDIA_TYPE
    assert result.media_type == "image/png"


@pytest.mark.asyncio
async def test_success_is_bounded_untrusted_and_does_not_send_credentials() -> None:
    seen_headers: httpx.Headers | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_headers
        seen_headers = request.headers
        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            content=b"hello",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SafeHTTPFetcher(resolver=_resolver, client=client).fetch(
            SafeFetchRequest(url="https://public.example/ok")
        )

    assert result.outcome is FetchOutcome.SUCCESS
    assert result.security is FetchSecurityClassification.UNTRUSTED_PUBLIC
    assert result.text == "hello"
    assert result.byte_count == 5
    assert seen_headers is not None
    assert "authorization" not in seen_headers
    assert "cookie" not in seen_headers


@pytest.mark.asyncio
async def test_sensitive_query_is_blocked_before_httpx_can_log_or_send_it() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="unexpected")

    secret = "do-not-leak-this-value"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SafeHTTPFetcher(resolver=_resolver, client=client).fetch(
            SafeFetchRequest(url=f"https://public.example/data?token={secret}")
        )

    assert result.outcome is FetchOutcome.BLOCKED
    assert result.error_code == "sensitive_query_parameter"
    assert secret not in result.model_dump_json()
    assert calls == 0
