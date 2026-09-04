"""GitHub REST discovery adapter with conservative eligibility and cursors."""

from __future__ import annotations

import hashlib
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from github_stars_contrib_mcp.application.discovery.github_eligibility import (
    GitHubEligibilityDecision,
    evaluate_github_item,
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

GITHUB_API_VERSION = "2026-03-10"
_RECENT_ID_LIMIT = 512
_NOTABLE_PATH_RE = re.compile(
    r"^/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(pulls|issues)/[1-9][0-9]*$"
)


def _metadata_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        normalized = value.strip()
        return (normalized,) if normalized else ()
    if not isinstance(value, (list, tuple, set, frozenset)):
        return ()
    return tuple(
        normalized
        for item in value
        if isinstance(item, str) and (normalized := item.strip())
    )


def _metadata_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _trusted_username(source: SourceRecord) -> str | None:
    configured = source.metadata.get("username")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    parts = urlsplit(source.url)
    if parts.scheme.lower() != "https" or parts.hostname != "github.com":
        return None
    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) != 1:
        return None
    return segments[0]


def _canonical_github_url(value: str) -> str | None:
    parts = urlsplit(value)
    if parts.scheme.lower() != "https" or parts.hostname != "github.com":
        return None
    path = "/" + "/".join(segment for segment in parts.path.split("/") if segment)
    return urlunsplit(("https", "github.com", path, parts.query, ""))


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


def _stable_id(kind: str, repository: str, payload: dict[str, Any], url: str) -> str:
    raw_id = payload.get("id") or payload.get("node_id")
    if raw_id is None:
        raw_id = hashlib.sha256(url.encode()).hexdigest()
    return f"github:{kind}:{repository}:{raw_id}"


def _evidence_id(source_id: str, external_id: str, url: str) -> str:
    material = f"{source_id}\0{external_id}\0{url}".encode()
    return f"evidence:{hashlib.sha256(material).hexdigest()}"


class GitHubSourceAdapter:
    """Discover explainable candidates from a trusted public GitHub identity."""

    name = "github"
    version = "1"

    def __init__(
        self,
        *,
        token: str | None = None,
        api_base_url: str = "https://api.github.com",
        user_agent: str = "github-stars-contrib-mcp-server/0.3.1",
        timeout_s: float = 10.0,
        max_repositories: int = 50,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token.strip() if isinstance(token, str) and token.strip() else None
        self._api_base_url = api_base_url.rstrip("/")
        self._user_agent = user_agent
        self._timeout_s = timeout_s
        self._max_repositories = max_repositories
        self._transport = transport
        self._auth_failed = False

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.GITHUB

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership is OwnershipStatus.REJECTED:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="source ownership was rejected",
            )
        if _trusted_username(source) is None:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="GitHub source must identify one trusted github.com username",
            )
        if self._auth_failed:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="GitHub discovery credentials were rejected",
                requires_credentials=True,
            )
        if self._token is None:
            return SourceCapability(
                status=CapabilityStatus.LIMITED,
                reason="anonymous GitHub REST access has lower rate limits",
                requires_credentials=False,
            )
        return SourceCapability(
            status=CapabilityStatus.AVAILABLE,
            permissions=("public repository metadata",),
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": self._user_agent,
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @staticmethod
    def _rate_limit_snapshot(headers: httpx.Headers) -> dict[str, str]:
        result: dict[str, str] = {}
        for source_name, target_name in (
            ("x-ratelimit-remaining", "remaining"),
            ("x-ratelimit-reset", "reset"),
            ("x-ratelimit-resource", "resource"),
        ):
            value = headers.get(source_name)
            if value is not None:
                result[target_name] = value
        return result

    async def _request(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        response = await client.get(url, headers=headers)
        if response.status_code == 429 or (
            response.status_code == 403
            and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise SourceAdapterError(
                AdapterErrorKind.RATE_LIMIT,
                "GitHub REST rate limit exhausted",
            )
        if response.status_code == 401 or (
            response.status_code == 403 and self._token is not None
        ):
            self._auth_failed = True
            raise SourceAdapterError(
                AdapterErrorKind.AUTH,
                "GitHub discovery credentials were rejected",
            )
        if response.status_code >= 400 and response.status_code != 304:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                f"GitHub REST request failed with HTTP {response.status_code}",
            )
        return response

    async def _collect_pages(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        etag: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, bool, dict[str, str]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = url
        first = True
        first_etag = etag
        rate_limit: dict[str, str] = {}
        for _ in range(20):
            if next_url is None:
                break
            conditional = {"If-None-Match": etag} if first and etag else None
            response = await self._request(client, next_url, headers=conditional)
            rate_limit = self._rate_limit_snapshot(response.headers) or rate_limit
            if first:
                first_etag = response.headers.get("etag") or etag
            if response.status_code == 304:
                return [], first_etag, True, rate_limit
            try:
                payload = response.json()
            except ValueError as exc:
                raise SourceAdapterError(
                    AdapterErrorKind.PARSE, "GitHub REST response was not valid JSON"
                ) from exc
            if not isinstance(payload, list):
                raise SourceAdapterError(
                    AdapterErrorKind.PARSE, "GitHub REST list endpoint returned an object"
                )
            items.extend(item for item in payload if isinstance(item, dict))
            next_link = response.links.get("next", {}).get("url")
            next_url = next_link if isinstance(next_link, str) else None
            first = False
        return items, first_etag, False, rate_limit

    async def _get_object(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        response = await self._request(client, url)
        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceAdapterError(
                AdapterErrorKind.PARSE, "GitHub REST response was not valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise SourceAdapterError(
                AdapterErrorKind.PARSE, "GitHub REST object endpoint returned a list"
            )
        return payload, self._rate_limit_snapshot(response.headers)

    @staticmethod
    def _release_emission(
        source: SourceRecord,
        repository: str,
        payload: dict[str, Any],
        decision: GitHubEligibilityDecision,
    ) -> AdapterEmission | None:
        raw_url = payload.get("html_url")
        if not isinstance(raw_url, str):
            return None
        url = _canonical_github_url(raw_url)
        if url is None:
            return None
        external_id = _stable_id("release", repository, payload, url)
        tag = payload.get("tag_name")
        name = payload.get("name")
        title = (
            str(name).strip()
            if isinstance(name, str) and name.strip()
            else f"{repository} {tag}".strip()
        )
        body = payload.get("body")
        description = str(body)[:4000] if isinstance(body, str) and body else None
        published_at = _parse_datetime(payload.get("published_at") or payload.get("created_at"))
        item = SourceItem(
            source_id=source.id,
            external_id=external_id,
            title=title,
            url=url,
            description=description,
            published_at=published_at,
            updated_at=_parse_datetime(payload.get("updated_at")),
            author=_trusted_username(source),
            type_hint=decision.contribution_type,
            metadata={
                "reason_code": decision.reason_code.value,
                "repository": repository,
                "github_id": payload.get("id"),
                "node_id": payload.get("node_id"),
            },
        )
        evidence = Evidence(
            id=_evidence_id(source.id, external_id, url),
            source_id=source.id,
            source_item_id=external_id,
            url=url,
            text_excerpt=description,
            data={
                "reason_code": decision.reason_code.value,
                "repository": repository,
                "github_id": payload.get("id"),
                "node_id": payload.get("node_id"),
                "tag_name": tag,
            },
        )
        return AdapterEmission(item=item, evidence=(evidence,))

    @staticmethod
    def _repository_emission(
        source: SourceRecord,
        payload: dict[str, Any],
        decision: GitHubEligibilityDecision,
    ) -> AdapterEmission | None:
        full_name = payload.get("full_name")
        raw_url = payload.get("html_url")
        if not isinstance(full_name, str) or "/" not in full_name or not isinstance(raw_url, str):
            return None
        url = _canonical_github_url(raw_url)
        if url is None:
            return None
        external_id = _stable_id("repository", full_name, payload, url)
        description = payload.get("description")
        item = SourceItem(
            source_id=source.id,
            external_id=external_id,
            title=full_name,
            url=url,
            description=description if isinstance(description, str) else None,
            published_at=_parse_datetime(payload.get("created_at")),
            updated_at=_parse_datetime(payload.get("updated_at")),
            author=_trusted_username(source),
            type_hint=decision.contribution_type,
            metadata={
                "reason_code": decision.reason_code.value,
                "repository": full_name,
                "github_id": payload.get("id"),
                "node_id": payload.get("node_id"),
            },
        )
        evidence = Evidence(
            id=_evidence_id(source.id, external_id, url),
            source_id=source.id,
            source_item_id=external_id,
            url=url,
            text_excerpt=item.description,
            data={
                "reason_code": decision.reason_code.value,
                "repository": full_name,
                "github_id": payload.get("id"),
                "node_id": payload.get("node_id"),
            },
        )
        return AdapterEmission(item=item, evidence=(evidence,))

    @staticmethod
    def _notable_emission(
        source: SourceRecord,
        api_path: str,
        payload: dict[str, Any],
        decision: GitHubEligibilityDecision,
    ) -> AdapterEmission | None:
        raw_url = payload.get("html_url")
        title = payload.get("title")
        if not isinstance(raw_url, str) or not isinstance(title, str) or not title.strip():
            return None
        url = _canonical_github_url(raw_url)
        if url is None:
            return None
        repository = "/".join(api_path.split("/")[2:4])
        kind = "pull_request" if "/pulls/" in api_path else "issue"
        external_id = _stable_id(kind, repository, payload, url)
        body = payload.get("body")
        description = str(body)[:4000] if isinstance(body, str) and body else None
        item = SourceItem(
            source_id=source.id,
            external_id=external_id,
            title=title.strip(),
            url=url,
            description=description,
            published_at=_parse_datetime(payload.get("created_at")),
            updated_at=_parse_datetime(payload.get("updated_at")),
            author=_trusted_username(source),
            type_hint=decision.contribution_type,
            metadata={
                "reason_code": decision.reason_code.value,
                "repository": repository,
                "api_path": api_path,
                "github_id": payload.get("id"),
                "node_id": payload.get("node_id"),
            },
        )
        evidence = Evidence(
            id=_evidence_id(source.id, external_id, url),
            source_id=source.id,
            source_item_id=external_id,
            url=url,
            text_excerpt=description,
            data={
                "reason_code": decision.reason_code.value,
                "repository": repository,
                "api_path": api_path,
                "github_id": payload.get("id"),
                "node_id": payload.get("node_id"),
            },
        )
        return AdapterEmission(item=item, evidence=(evidence,))

    @staticmethod
    def _append_if_new(
        emissions: list[AdapterEmission],
        emission: AdapterEmission | None,
        seen_ids: set[str],
    ) -> None:
        if emission is None or emission.item.external_id in seen_ids:
            return
        seen_ids.add(emission.item.external_id)
        emissions.append(emission)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        username = _trusted_username(source)
        if username is None:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                "GitHub source does not identify one trusted username",
            )

        prior_recent_ids = [
            value
            for value in _metadata_values((cursor or {}).get("recent_ids"))
        ]
        seen_ids = set(prior_recent_ids)
        prior_etags = (cursor or {}).get("release_etags")
        release_etags = (
            {str(key): str(value) for key, value in prior_etags.items()}
            if isinstance(prior_etags, dict)
            else {}
        )

        configured_repositories = set(_metadata_values(source.metadata.get("repositories")))
        candidate_repositories = set(
            _metadata_values(source.metadata.get("candidate_repositories"))
        )
        include_repositories = _metadata_bool(
            source.metadata.get("include_repositories"), False
        )
        include_releases = _metadata_bool(source.metadata.get("include_releases"), True)
        notable_paths = _metadata_values(source.metadata.get("notable_api_paths"))

        emissions: list[AdapterEmission] = []
        latest_rate_limit: dict[str, str] = {}
        headers = self._headers()

        async with httpx.AsyncClient(
            base_url=self._api_base_url,
            headers=headers,
            timeout=self._timeout_s,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            repositories, _, _, latest_rate_limit = await self._collect_pages(
                client,
                f"/users/{username}/repos?type=owner&sort=updated&direction=desc&per_page=100",
            )
            repositories = repositories[: self._max_repositories]
            for repository in repositories:
                full_name = repository.get("full_name")
                if not isinstance(full_name, str) or "/" not in full_name:
                    continue
                if configured_repositories and full_name not in configured_repositories:
                    continue

                explicit_repo_candidate = (
                    include_repositories or full_name in candidate_repositories
                )
                repo_decision = evaluate_github_item(
                    "repository",
                    repository,
                    trusted_username=username,
                    explicitly_configured=explicit_repo_candidate,
                )
                if repo_decision.eligible:
                    self._append_if_new(
                        emissions,
                        self._repository_emission(source, repository, repo_decision),
                        seen_ids,
                    )

                if not include_releases:
                    continue
                releases_url = f"/repos/{full_name}/releases?per_page=100"
                releases, new_etag, _, rate_limit = await self._collect_pages(
                    client,
                    releases_url,
                    etag=release_etags.get(full_name),
                )
                if rate_limit:
                    latest_rate_limit = rate_limit
                if new_etag:
                    release_etags[full_name] = new_etag
                for release in releases:
                    enriched = dict(release)
                    enriched["repository"] = repository
                    decision = evaluate_github_item(
                        "release",
                        enriched,
                        trusted_username=username,
                    )
                    if decision.eligible:
                        self._append_if_new(
                            emissions,
                            self._release_emission(
                                source,
                                full_name,
                                enriched,
                                decision,
                            ),
                            seen_ids,
                        )

            for api_path in notable_paths:
                if _NOTABLE_PATH_RE.fullmatch(api_path) is None:
                    continue
                payload, rate_limit = await self._get_object(client, api_path)
                if rate_limit:
                    latest_rate_limit = rate_limit
                kind = "pull_request" if "/pulls/" in api_path else "issue"
                decision = evaluate_github_item(
                    kind,
                    payload,
                    trusted_username=username,
                    explicitly_configured=True,
                )
                if decision.eligible:
                    self._append_if_new(
                        emissions,
                        self._notable_emission(source, api_path, payload, decision),
                        seen_ids,
                    )

        new_ids = [emission.item.external_id for emission in emissions]
        next_recent = list(dict.fromkeys([*new_ids, *prior_recent_ids]))[
            :_RECENT_ID_LIMIT
        ]
        yield SourceBatch(
            emissions=tuple(emissions),
            next_cursor={
                "recent_ids": next_recent,
                "release_etags": dict(sorted(release_etags.items())),
                "rate_limit": latest_rate_limit,
            },
        )
