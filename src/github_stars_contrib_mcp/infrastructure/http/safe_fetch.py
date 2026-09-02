"""SSRF-safe bounded HTTP fetcher for untrusted discovery content."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from collections.abc import Awaitable, Callable, Sequence
from urllib.parse import urljoin, urlsplit

import httpx

from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    FetchOutcome,
    FetchSecurityClassification,
    SafeFetchRequest,
    SafeFetchResult,
    has_sensitive_query,
    redact_secret_text,
    redact_url,
)

logger = logging.getLogger(__name__)

Resolver = Callable[[str], Awaitable[Sequence[str]]]
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_BLOCKED_HOSTNAMES = {
    "instance-data.ec2.internal",
    "metadata.azure.internal",
    "metadata.google.internal",
}


async def _default_resolver(hostname: str) -> Sequence[str]:
    """Resolve a hostname without blocking the event loop."""

    def _resolve() -> list[str]:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        return sorted({str(item[4][0]) for item in infos})

    return await asyncio.to_thread(_resolve)


def _public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_global and not (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )


def _media_allowed(media_type: str, allowlist: tuple[str, ...]) -> bool:
    media = media_type.lower()
    for item in allowlist:
        rule = item.lower()
        if rule == media:
            return True
        if rule.endswith("/*") and media.startswith(rule[:-1]):
            return True
    return False


def _charset(content_type: str) -> str:
    for part in content_type.split(";")[1:]:
        key, separator, value = part.strip().partition("=")
        if separator and key.lower() == "charset":
            candidate = value.strip().strip("\"'")
            if candidate:
                return candidate
    return "utf-8"


class SafeHTTPFetcher:
    """Fetch public HTTP(S) content without forwarding application credentials."""

    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        client: httpx.AsyncClient | None = None,
        user_agent: str = "github-stars-contrib-mcp-server/safe-fetch",
    ) -> None:
        self._resolver = resolver or _default_resolver
        self._client = client
        self._user_agent = user_agent

    async def _target_error(self, url: str) -> str | None:
        try:
            parsed = urlsplit(url)
        except ValueError:
            return "invalid_url"

        if parsed.scheme.lower() not in {"http", "https"}:
            return "unsupported_scheme"
        if parsed.username is not None or parsed.password is not None:
            return "userinfo_not_allowed"
        try:
            parsed.port
        except ValueError:
            return "invalid_port"
        if has_sensitive_query(url):
            return "sensitive_query_parameter"

        hostname = (parsed.hostname or "").rstrip(".").lower()
        if not hostname:
            return "missing_hostname"
        if "%" in hostname:
            return "zone_identifier_not_allowed"
        if (
            hostname == "localhost"
            or hostname.endswith(".localhost")
            or hostname in _BLOCKED_HOSTNAMES
        ):
            return "unsafe_hostname"

        try:
            literal = ipaddress.ip_address(hostname)
        except ValueError:
            try:
                resolved = await self._resolver(hostname)
            except OSError:
                return "dns_resolution_failed"
            if not resolved:
                return "dns_no_address"
            if not all(_public_ip(address) for address in resolved):
                return "unsafe_address"
        else:
            if not _public_ip(str(literal)):
                return "unsafe_address"

        return None

    @staticmethod
    def _result(
        url: str,
        *,
        outcome: FetchOutcome,
        security: FetchSecurityClassification,
        status_code: int | None = None,
        media_type: str | None = None,
        text: str | None = None,
        byte_count: int = 0,
        redirect_count: int = 0,
        truncated: bool = False,
        error_code: str | None = None,
    ) -> SafeFetchResult:
        return SafeFetchResult(
            final_url=redact_url(url),
            outcome=outcome,
            security=security,
            status_code=status_code,
            media_type=media_type,
            text=text,
            byte_count=byte_count,
            redirect_count=redirect_count,
            truncated=truncated,
            error_code=error_code,
        )

    @staticmethod
    def _log_result(result: SafeFetchResult) -> None:
        logger.info(
            "safe_fetch_result",
            extra={
                "outcome": result.outcome.value,
                "status_code": result.status_code,
                "media_type": result.media_type,
                "byte_count": result.byte_count,
                "redirect_count": result.redirect_count,
                "error_code": result.error_code,
            },
        )

    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        timeout = httpx.Timeout(
            request.read_timeout_s,
            connect=request.connect_timeout_s,
            write=request.read_timeout_s,
            pool=request.connect_timeout_s,
        )
        if self._client is not None:
            result = await self._fetch_with_client(self._client, request, timeout)
        else:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                result = await self._fetch_with_client(client, request, timeout)
        self._log_result(result)
        return result

    async def _fetch_with_client(
        self,
        client: httpx.AsyncClient,
        request: SafeFetchRequest,
        timeout: httpx.Timeout,
    ) -> SafeFetchResult:
        current_url = request.url
        redirects = 0
        headers = {
            "Accept": ", ".join(request.allowed_media_types),
            "User-Agent": self._user_agent,
        }

        while True:
            policy_error = await self._target_error(current_url)
            if policy_error is not None:
                security = (
                    FetchSecurityClassification.NOT_FETCHED
                    if policy_error.startswith("dns_")
                    else FetchSecurityClassification.BLOCKED_UNSAFE_TARGET
                )
                outcome = (
                    FetchOutcome.NETWORK_ERROR
                    if policy_error.startswith("dns_")
                    else FetchOutcome.BLOCKED
                )
                return self._result(
                    current_url,
                    outcome=outcome,
                    security=security,
                    redirect_count=redirects,
                    error_code=policy_error,
                )

            try:
                async with client.stream(
                    "GET",
                    current_url,
                    headers=headers,
                    follow_redirects=False,
                    timeout=timeout,
                ) as response:
                    status = response.status_code
                    if status in _REDIRECT_STATUSES:
                        location = response.headers.get("location")
                        if not location:
                            return self._result(
                                current_url,
                                outcome=FetchOutcome.HTTP_ERROR,
                                security=FetchSecurityClassification.NOT_FETCHED,
                                status_code=status,
                                redirect_count=redirects,
                                error_code="redirect_without_location",
                            )
                        if redirects >= request.max_redirects:
                            return self._result(
                                current_url,
                                outcome=FetchOutcome.TOO_MANY_REDIRECTS,
                                security=FetchSecurityClassification.NOT_FETCHED,
                                status_code=status,
                                redirect_count=redirects,
                                error_code="redirect_limit",
                            )
                        current_url = urljoin(current_url, location)
                        redirects += 1
                        continue

                    if status < 200 or status >= 300:
                        return self._result(
                            current_url,
                            outcome=FetchOutcome.HTTP_ERROR,
                            security=FetchSecurityClassification.NOT_FETCHED,
                            status_code=status,
                            redirect_count=redirects,
                            error_code="http_status",
                        )

                    raw_content_type = response.headers.get("content-type", "")
                    media_type = raw_content_type.split(";", 1)[0].strip().lower()
                    if not media_type or not _media_allowed(
                        media_type, request.allowed_media_types
                    ):
                        return self._result(
                            current_url,
                            outcome=FetchOutcome.UNSUPPORTED_MEDIA_TYPE,
                            security=FetchSecurityClassification.NOT_FETCHED,
                            status_code=status,
                            media_type=media_type or None,
                            redirect_count=redirects,
                            error_code="unsupported_media_type",
                        )

                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            advertised_size = int(content_length)
                        except ValueError:
                            advertised_size = 0
                        if advertised_size > request.max_bytes:
                            return self._result(
                                current_url,
                                outcome=FetchOutcome.TOO_LARGE,
                                security=FetchSecurityClassification.NOT_FETCHED,
                                status_code=status,
                                media_type=media_type,
                                byte_count=advertised_size,
                                redirect_count=redirects,
                                truncated=True,
                                error_code="content_length_limit",
                            )

                    chunks: list[bytes] = []
                    byte_count = 0
                    chunk_size = min(65_536, request.max_bytes + 1)
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        byte_count += len(chunk)
                        if byte_count > request.max_bytes:
                            return self._result(
                                current_url,
                                outcome=FetchOutcome.TOO_LARGE,
                                security=FetchSecurityClassification.NOT_FETCHED,
                                status_code=status,
                                media_type=media_type,
                                byte_count=byte_count,
                                redirect_count=redirects,
                                truncated=True,
                                error_code="body_size_limit",
                            )
                        chunks.append(chunk)

                    body = b"".join(chunks)
                    try:
                        decoded = body.decode(_charset(raw_content_type), errors="replace")
                    except LookupError:
                        decoded = body.decode("utf-8", errors="replace")
                    return self._result(
                        current_url,
                        outcome=FetchOutcome.SUCCESS,
                        security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
                        status_code=status,
                        media_type=media_type,
                        text=redact_secret_text(decoded),
                        byte_count=len(body),
                        redirect_count=redirects,
                    )
            except (httpx.RequestError, httpx.InvalidURL):
                return self._result(
                    current_url,
                    outcome=FetchOutcome.NETWORK_ERROR,
                    security=FetchSecurityClassification.NOT_FETCHED,
                    redirect_count=redirects,
                    error_code="network_error",
                )
