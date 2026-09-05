"""YouTube Data API v3 discovery adapter."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx

from github_stars_contrib_mcp.application.discovery.youtube_identity import (
    normalize_youtube_channel,
    source_channel_id,
)
from github_stars_contrib_mcp.domain.discovery import (
    Evidence,
    OwnershipStatus,
    SourceItem,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterEmission,
    AdapterErrorKind,
    CapabilityStatus,
    SourceAdapterError,
    SourceBatch,
    SourceCapability,
)
from github_stars_contrib_mcp.models import ContributionType

_RECENT_ID_LIMIT = 512
_QUOTA_REASONS = {
    "dailyLimitExceeded",
    "quotaExceeded",
    "rateLimitExceeded",
    "userRateLimitExceeded",
}
_AUTH_REASONS = {
    "accessNotConfigured",
    "forbidden",
    "ipRefererBlocked",
    "keyInvalid",
}


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _evidence_id(source_id: str, video_id: str) -> str:
    material = f"{source_id}\0{video_id}".encode()
    return f"evidence:{hashlib.sha256(material).hexdigest()}"


def _error_reasons(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    error = payload.get("error")
    if not isinstance(error, dict):
        return set()

    reasons: set[str] = set()
    values = error.get("errors")
    if isinstance(values, list):
        for item in values:
            if isinstance(item, dict) and isinstance(item.get("reason"), str):
                reasons.add(item["reason"])
    status = error.get("status")
    if isinstance(status, str):
        reasons.add(status)
    return reasons


class YouTubeSourceAdapter:
    """Discover uploads from a trusted YouTube channel through Data API v3."""

    name = "youtube"
    version = "1"
    api_base_url = "https://www.googleapis.com/youtube/v3"

    def __init__(
        self,
        *,
        api_key: str | None,
        timeout_s: float = 10.0,
        max_pages: int = 10,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = (
            api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        )
        self._timeout_s = timeout_s
        self._max_pages = max_pages
        self._transport = transport
        self._auth_failed = False

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.YOUTUBE

    def _identity_query(self, source: SourceRecord) -> tuple[str, str] | None:
        channel_id = source_channel_id(source.url, source.metadata)
        if channel_id:
            return "id", channel_id

        try:
            identity = normalize_youtube_channel(source.url)
        except ValueError:
            return None
        if identity.handle:
            return "forHandle", f"@{identity.handle}"
        if identity.legacy_username:
            return "forUsername", identity.legacy_username
        return None

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership is OwnershipStatus.REJECTED:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="source ownership was rejected",
            )
        if self._api_key is None:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="YouTube Data API key is not configured",
                requires_credentials=True,
            )
        if self._auth_failed:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="YouTube Data API credentials were rejected",
                requires_credentials=True,
            )
        if self._identity_query(source) is None:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason=(
                    "YouTube Data API requires a channel ID, handle, legacy username, "
                    "or trusted youtube_channel_id metadata"
                ),
            )
        return SourceCapability(
            status=CapabilityStatus.AVAILABLE,
            requires_credentials=True,
            permissions=("public YouTube channel and video metadata",),
        )

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        request_params = {**params, "key": self._api_key or ""}
        response = await client.get(
            f"{self.api_base_url}/{path}", params=request_params
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceAdapterError(
                AdapterErrorKind.PARSE,
                "YouTube API returned invalid JSON",
            ) from exc

        reasons = _error_reasons(payload)
        if response.status_code == 429 or reasons & _QUOTA_REASONS:
            raise SourceAdapterError(
                AdapterErrorKind.RATE_LIMIT,
                "YouTube Data API quota was exhausted",
            )
        if response.status_code == 401 or reasons & _AUTH_REASONS:
            self._auth_failed = True
            raise SourceAdapterError(
                AdapterErrorKind.AUTH,
                "YouTube Data API credentials were rejected",
            )
        if response.status_code >= 400:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                f"YouTube Data API request failed with HTTP {response.status_code}",
            )
        if not isinstance(payload, dict):
            raise SourceAdapterError(
                AdapterErrorKind.PARSE,
                "YouTube Data API returned a non-object payload",
            )
        return payload

    async def _resolve_channel(
        self,
        client: httpx.AsyncClient,
        source: SourceRecord,
    ) -> tuple[str, str, str | None]:
        query = self._identity_query(source)
        if query is None:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                "YouTube channel identity is unresolved",
            )

        key, value = query
        payload = await self._get(
            client,
            "channels",
            {
                "part": "contentDetails,snippet",
                key: value,
                "maxResults": "1",
            },
        )
        items = payload.get("items")
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                "YouTube channel was not found",
            )

        channel = items[0]
        channel_id = channel.get("id")
        details = channel.get("contentDetails")
        snippet = channel.get("snippet")
        if (
            not isinstance(channel_id, str)
            or not isinstance(details, dict)
            or not isinstance(details.get("relatedPlaylists"), dict)
            or not isinstance(details["relatedPlaylists"].get("uploads"), str)
        ):
            raise SourceAdapterError(
                AdapterErrorKind.PARSE,
                "YouTube channel payload lacked uploads playlist metadata",
            )

        title = snippet.get("title") if isinstance(snippet, dict) else None
        return (
            channel_id,
            details["relatedPlaylists"]["uploads"],
            title if isinstance(title, str) else None,
        )

    async def _video_metadata(
        self,
        client: httpx.AsyncClient,
        video_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not video_ids:
            return {}
        payload = await self._get(
            client,
            "videos",
            {
                "part": "snippet,status",
                "id": ",".join(video_ids),
                "maxResults": "50",
            },
        )
        items = payload.get("items")
        if not isinstance(items, list):
            raise SourceAdapterError(
                AdapterErrorKind.PARSE,
                "YouTube videos payload lacked items",
            )
        return {
            item["id"]: item
            for item in items
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    @staticmethod
    def _emission(
        source: SourceRecord,
        *,
        channel_id: str,
        channel_title: str | None,
        video_id: str,
        payload: dict[str, Any],
    ) -> AdapterEmission | None:
        snippet = payload.get("snippet")
        status = payload.get("status")
        if not isinstance(snippet, dict):
            return None
        if isinstance(status, dict) and status.get("privacyStatus") not in {
            None,
            "public",
        }:
            return None

        title = snippet.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        url = f"https://www.youtube.com/watch?v={video_id}"
        description = snippet.get("description")
        description = (
            description[:4000]
            if isinstance(description, str) and description.strip()
            else None
        )
        published_at = _parse_datetime(snippet.get("publishedAt"))
        external_id = f"youtube:video:{video_id}"
        item = SourceItem(
            source_id=source.id,
            external_id=external_id,
            title=title.strip(),
            url=url,
            description=description,
            published_at=published_at,
            author=channel_title,
            type_hint=ContributionType.VIDEO_PODCAST,
            metadata={
                "channel_id": channel_id,
                "video_id": video_id,
                "discovery_mode": "data_api",
            },
        )
        evidence = Evidence(
            id=_evidence_id(source.id, video_id),
            source_id=source.id,
            source_item_id=external_id,
            url=url,
            text_excerpt=description,
            data={
                "channel_id": channel_id,
                "video_id": video_id,
                "published_at": (
                    published_at.isoformat() if published_at is not None else None
                ),
                "discovery_mode": "data_api",
            },
        )
        return AdapterEmission(item=item, evidence=(evidence,))

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        if self._api_key is None:
            raise SourceAdapterError(
                AdapterErrorKind.AUTH,
                "YouTube Data API key is not configured",
            )

        timeout = httpx.Timeout(self._timeout_s)
        async with httpx.AsyncClient(
            timeout=timeout,
            transport=self._transport,
            trust_env=False,
        ) as client:
            channel_id, uploads_playlist, channel_title = await self._resolve_channel(
                client, source
            )
            recent = [
                str(item)
                for item in (cursor or {}).get("recent_ids", [])
                if isinstance(item, str)
            ]
            recent_set = set(recent)
            page_token: str | None = None

            for _ in range(self._max_pages):
                params = {
                    "part": "contentDetails",
                    "playlistId": uploads_playlist,
                    "maxResults": "50",
                }
                if page_token:
                    params["pageToken"] = page_token

                page = await self._get(client, "playlistItems", params)
                items = page.get("items")
                if not isinstance(items, list):
                    raise SourceAdapterError(
                        AdapterErrorKind.PARSE,
                        "YouTube uploads playlist payload lacked items",
                    )

                page_video_ids = [
                    video_id
                    for item in items
                    if isinstance(item, dict)
                    and isinstance(item.get("contentDetails"), dict)
                    and isinstance(
                        video_id := item["contentDetails"].get("videoId"), str
                    )
                ]
                new_video_ids = [
                    video_id
                    for video_id in page_video_ids
                    if video_id not in recent_set
                ]
                metadata = await self._video_metadata(client, new_video_ids)

                emissions: list[AdapterEmission] = []
                for video_id in new_video_ids:
                    payload = metadata.get(video_id)
                    if payload is None:
                        continue
                    emission = self._emission(
                        source,
                        channel_id=channel_id,
                        channel_title=channel_title,
                        video_id=video_id,
                        payload=payload,
                    )
                    if emission is not None:
                        emissions.append(emission)

                next_recent = list(dict.fromkeys([*page_video_ids, *recent]))[
                    :_RECENT_ID_LIMIT
                ]
                next_cursor = {
                    "channel_id": channel_id,
                    "uploads_playlist": uploads_playlist,
                    "recent_ids": next_recent,
                }
                yield SourceBatch(
                    emissions=tuple(emissions),
                    next_cursor=next_cursor,
                )

                recent = next_recent
                recent_set = set(recent)
                next_value = page.get("nextPageToken")
                page_token = next_value if isinstance(next_value, str) else None
                if page_token is None or not new_video_ids:
                    break
