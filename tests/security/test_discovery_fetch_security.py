from __future__ import annotations

import logging

import httpx
import pytest

from github_stars_contrib_mcp.application.discovery.untrusted_content import (
    sanitize_untrusted_content,
)
from github_stars_contrib_mcp.config.settings import Settings
from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    FetchOutcome,
    SafeFetchRequest,
)
from github_stars_contrib_mcp.infrastructure.http.safe_fetch import SafeHTTPFetcher


async def _public_resolver(hostname: str) -> list[str]:
    del hostname
    return ["93.184.216.34"]


def test_fetch_settings_are_conservative_and_bounded() -> None:
    settings = Settings()
    assert 0 < settings.discovery_fetch_connect_timeout_s <= 5
    assert 0 < settings.discovery_fetch_read_timeout_s <= 15
    assert settings.discovery_fetch_max_bytes <= 1_000_000
    assert settings.discovery_fetch_max_redirects <= 3
    assert settings.discovery_untrusted_excerpt_max_chars <= 10_000


@pytest.mark.asyncio
async def test_remote_secret_like_text_is_redacted_from_result_evidence_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "a-very-sensitive-token-value"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain"},
            text=f"STARS_API_TOKEN={secret}",
        )

    caplog.set_level(logging.INFO)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SafeHTTPFetcher(resolver=_public_resolver, client=client).fetch(
            SafeFetchRequest(url="https://public.example/article")
        )

    evidence = sanitize_untrusted_content(
        result.text or "",
        media_type=result.media_type or "text/plain",
        source_url=result.final_url,
    )

    assert result.outcome is FetchOutcome.SUCCESS
    assert secret not in result.model_dump_json()
    assert secret not in evidence.model_dump_json()
    assert secret not in caplog.text
    assert "[REDACTED]" in (result.text or "")


@pytest.mark.asyncio
async def test_credentials_in_url_are_blocked_before_request_or_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "query-secret-value"
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="unexpected")

    caplog.set_level(logging.INFO)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SafeHTTPFetcher(resolver=_public_resolver, client=client).fetch(
            SafeFetchRequest(url=f"https://public.example/?access_token={secret}")
        )

    assert result.outcome is FetchOutcome.BLOCKED
    assert calls == 0
    assert secret not in result.model_dump_json()
    assert secret not in caplog.text
