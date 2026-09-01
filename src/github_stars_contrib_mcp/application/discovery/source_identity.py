"""Deterministic source URL canonicalization and provider classification."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from github_stars_contrib_mcp.domain.discovery import SourceType

_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "utm_campaign",
    "utm_content",
    "utm_id",
    "utm_medium",
    "utm_source",
    "utm_term",
}
_PROVIDER_HOST_ALIASES = {
    "www.github.com": "github.com",
    "www.youtube.com": "youtube.com",
    "m.youtube.com": "youtube.com",
    "www.linkedin.com": "linkedin.com",
    "twitter.com": "x.com",
    "www.twitter.com": "x.com",
    "www.x.com": "x.com",
}


@dataclass(frozen=True, slots=True)
class CanonicalSource:
    source_id: str
    canonical_url: str
    source_type: SourceType
    host: str


def _normalize_input(url: str) -> str:
    value = url.strip()
    if not value:
        raise ValueError("source URL must not be empty")
    if "://" not in value:
        value = f"https://{value}"
    return value


def classify_source_type(host: str, path: str = "") -> SourceType:
    """Classify a canonical host/path without fetching it."""

    host = _PROVIDER_HOST_ALIASES.get(host.lower(), host.lower())
    normalized_path = path.lower().rstrip("/")
    if host == "github.com" or host.endswith(".github.com"):
        return SourceType.GITHUB
    if host in {"youtube.com", "youtu.be"}:
        return SourceType.YOUTUBE
    if host == "sessionize.com" or host.endswith(".sessionize.com"):
        return SourceType.SESSIONIZE
    if "pretalx" in host:
        return SourceType.PRETALX
    if host == "x.com":
        return SourceType.X
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        return SourceType.LINKEDIN
    if (
        normalized_path.endswith((".rss", ".xml", ".atom"))
        or normalized_path.endswith(("/feed", "/rss", "/atom"))
    ):
        return SourceType.RSS
    return SourceType.WEBSITE


def canonicalize_source_url(url: str) -> CanonicalSource:
    """Return a stable URL/source identity for one explicitly supplied source."""

    parsed = urlsplit(_normalize_input(url))
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("source URL scheme must be http or https")
    if not parsed.hostname:
        raise ValueError("source URL must include a hostname")

    host = parsed.hostname.rstrip(".").lower().encode("idna").decode("ascii")
    host = _PROVIDER_HOST_ALIASES.get(host, host)

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("source URL contains an invalid port") from exc
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = host if port is None or default_port else f"{host}:{port}"

    path = parsed.path or ""
    if path == "/":
        path = ""
    elif path.endswith("/"):
        path = path.rstrip("/")

    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS
    ]
    query = urlencode(sorted(query_items))
    source_type = classify_source_type(host, path)
    canonical_url = urlunsplit((scheme, netloc, path, query, ""))
    return CanonicalSource(
        source_id=f"{source_type.value}:{canonical_url}",
        canonical_url=canonical_url,
        source_type=source_type,
        host=host,
    )


def canonical_origin(url: str) -> CanonicalSource:
    """Reduce a contribution URL to a provider-classified origin."""

    canonical = canonicalize_source_url(url)
    parsed = urlsplit(canonical.canonical_url)
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    return CanonicalSource(
        source_id=f"{canonical.source_type.value}:{origin}",
        canonical_url=origin,
        source_type=canonical.source_type,
        host=canonical.host,
    )
