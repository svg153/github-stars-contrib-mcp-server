"""Normalize trusted YouTube channel identities without scraping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

_CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{20,30}$")
_ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}


@dataclass(frozen=True, slots=True)
class YouTubeChannelIdentity:
    """Normalized YouTube channel locator."""

    channel_id: str | None = None
    handle: str | None = None
    legacy_username: str | None = None
    custom_name: str | None = None
    canonical_url: str = ""
    needs_api_resolution: bool = False

    @property
    def registry_key(self) -> str:
        if self.channel_id:
            return f"channel:{self.channel_id}"
        if self.handle:
            return f"handle:{self.handle.casefold()}"
        if self.legacy_username:
            return f"user:{self.legacy_username.casefold()}"
        if self.custom_name:
            return f"custom:{self.custom_name.casefold()}"
        raise ValueError("YouTube identity has no usable locator")


def _validated_channel_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not _CHANNEL_ID_RE.fullmatch(normalized):
        raise ValueError("invalid YouTube channel ID")
    return normalized


def normalize_youtube_channel(
    url: str,
    *,
    known_channel_id: str | None = None,
) -> YouTubeChannelIdentity:
    """Normalize channel URLs; never infer ownership from a video URL."""

    resolved_channel_id = _validated_channel_id(known_channel_id)
    if resolved_channel_id:
        return YouTubeChannelIdentity(
            channel_id=resolved_channel_id,
            canonical_url=f"https://www.youtube.com/channel/{resolved_channel_id}",
        )

    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme.lower() != "https" or host not in _ALLOWED_HOSTS:
        raise ValueError("YouTube source must use an https youtube.com channel URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("YouTube source URL cannot contain userinfo")

    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        raise ValueError("YouTube source must identify one channel")
    if segments[0] in {"watch", "shorts", "live", "embed", "playlist"}:
        raise ValueError("video or playlist URLs are not channel identities")

    if segments[0] == "channel" and len(segments) == 2:
        channel_id = _validated_channel_id(segments[1])
        return YouTubeChannelIdentity(
            channel_id=channel_id,
            canonical_url=f"https://www.youtube.com/channel/{channel_id}",
        )

    if len(segments) == 1 and segments[0].startswith("@"):
        handle = segments[0][1:].strip()
        if not handle:
            raise ValueError("empty YouTube handle")
        normalized_handle = handle.casefold()
        return YouTubeChannelIdentity(
            handle=normalized_handle,
            canonical_url=f"https://www.youtube.com/@{normalized_handle}",
            needs_api_resolution=True,
        )

    if len(segments) == 2 and segments[0] == "user":
        username = segments[1].strip()
        if not username:
            raise ValueError("empty YouTube legacy username")
        return YouTubeChannelIdentity(
            legacy_username=username,
            canonical_url=urlunsplit(
                ("https", "www.youtube.com", f"/user/{username}", "", "")
            ),
            needs_api_resolution=True,
        )

    if len(segments) == 2 and segments[0] == "c":
        custom_name = segments[1].strip()
        if not custom_name:
            raise ValueError("empty YouTube custom channel name")
        return YouTubeChannelIdentity(
            custom_name=custom_name,
            canonical_url=urlunsplit(
                ("https", "www.youtube.com", f"/c/{custom_name}", "", "")
            ),
            needs_api_resolution=True,
        )

    raise ValueError("unsupported YouTube channel URL shape")


def source_channel_id(url: str, metadata: dict[str, object]) -> str | None:
    """Return a canonical channel ID from trusted source data when known."""

    configured = metadata.get("youtube_channel_id") or metadata.get("channel_id")
    if isinstance(configured, str) and configured.strip():
        return _validated_channel_id(configured)
    try:
        return normalize_youtube_channel(url).channel_id
    except ValueError:
        return None
