from __future__ import annotations

from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    ContentFetcher,
    FetchOutcome,
    FetchSecurityClassification,
    SafeFetchRequest,
    SafeFetchResult,
    redact_secret_text,
    redact_url,
)


class FakeFetcher:
    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type="text/plain",
            text="ok",
            byte_count=2,
        )


def test_contract_is_runtime_fakeable() -> None:
    assert isinstance(FakeFetcher(), ContentFetcher)


def test_request_exposes_policy_hooks_and_bounded_defaults() -> None:
    request = SafeFetchRequest(url="https://example.com/feed")
    assert request.robots_policy == "respect"
    assert request.cache_policy == "default"
    assert request.max_redirects == 3
    assert request.max_bytes == 1_000_000


def test_redaction_helpers_remove_credentials() -> None:
    url = redact_url("https://example.com/?token=super-secret&view=public")
    text = redact_secret_text(
        "STARS_API_TOKEN=super-secret Bearer abcdefghijklmnop ghp_abcdefghijklmnop"
    )
    assert "super-secret" not in url
    assert "super-secret" not in text
    assert "abcdefghijklmnop" not in text
