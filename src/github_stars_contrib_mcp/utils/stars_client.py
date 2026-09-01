"""GitHub Stars API client.

Contribution writes/reads use the REST API introduced in August 2026.
Profile and link operations remain on the legacy GraphQL endpoint until GitHub
publishes equivalent supported REST endpoints for those surfaces.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import APIResult
from .queries import (
    CREATE_LINK_MUTATION,
    DELETE_LINK_MUTATION,
    GET_STARS_QUERY,
    UPDATE_LINK_MUTATION,
    UPDATE_PROFILE_MUTATION,
    USER_DATA_QUERY,
    USER_QUERY,
)

logger = structlog.get_logger(__name__)
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,255}$")


class StarsClient:
    def __init__(
        self,
        api_url: str,
        token: str,
        contributions_api_url: str = "https://stars.github.com/api/contributions",
    ) -> None:
        self.api_url = api_url.rstrip("/") + "/"
        self.contributions_api_url = contributions_api_url.rstrip("/")
        self.token = token
        self._headers = {
            "Content-Type": "application/json",
            "Origin": "https://stars.github.com",
            "Referer": "https://stars.github.com/",
            "User-Agent": "github-stars-contrib-mcp-server/0.2.0",
            "Accept": "application/json",
        }
        self._cookies = {"token": self.token}
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"

    # Current REST Contributions API -------------------------------------
    async def validate_token(self) -> APIResult:
        """Validate auth using the supported Contributions REST API."""
        return await self.list_contributions(page=1)

    async def list_contributions(self, page: int = 1) -> APIResult:
        if page < 1:
            return APIResult(False, None, "page must be >= 1")
        return APIResult(
            **await self._execute_rest(
                "GET", params={"page": page}, op="listContributions"
            )
        )

    async def create_contributions(self, items: list[dict[str, Any]]) -> APIResult:
        result = await self._execute_rest(
            "POST", json_body={"data": items}, op="createContributions"
        )
        if not result["ok"]:
            return APIResult(False, None, result["error"])

        body = result["data"] or {}
        contributions = body.get("data", []) if isinstance(body, dict) else []
        if not isinstance(contributions, list):
            contributions = [contributions]
        ids = [
            item.get("id")
            for item in contributions
            if isinstance(item, dict) and item.get("id")
        ]
        return APIResult(True, {"ids": ids, "contributions": contributions})

    async def create_contribution(
        self, type: str, date: str, title: str, url: str, description: str
    ) -> APIResult:
        result = await self.create_contributions(
            [
                {
                    "type": type,
                    "date": date,
                    "title": title,
                    "url": url,
                    "description": description,
                }
            ]
        )
        if not result.ok:
            return result
        contributions = (result.data or {}).get("contributions", [])
        contribution = contributions[0] if contributions else None
        return APIResult(True, {"createContribution": contribution})

    async def upsert_contribution(
        self, client_id: str, data: dict[str, Any]
    ) -> APIResult:
        """Idempotently create or replace a contribution by REST client ID."""
        if not _CLIENT_ID_RE.fullmatch(client_id):
            return APIResult(
                False,
                None,
                "client ID must be 1-255 characters using letters, numbers, '.', '_', ':', or '-'",
            )
        result = await self._execute_rest(
            "PUT",
            path=f"/{quote(client_id, safe='')}",
            json_body=data,
            op="upsertContribution",
        )
        if not result["ok"]:
            return APIResult(False, None, result["error"])
        body = result["data"] or {}
        contributions = body.get("data", []) if isinstance(body, dict) else []
        if isinstance(contributions, list):
            contribution = contributions[0] if contributions else None
        else:
            contribution = contributions
        return APIResult(True, {"upsertContribution": contribution})

    async def update_contribution(
        self, contribution_id: str, data: dict[str, Any]
    ) -> APIResult:
        """Reject the retired server-ID partial update contract.

        The new REST PUT key is a caller-controlled client ID, not the old
        GraphQL contribution ID, so silently forwarding this method could create
        a duplicate contribution.
        """
        return APIResult(
            False,
            None,
            "update_contribution is retired: use upsert_contribution with a stable caller-controlled client ID and a complete payload",
        )

    async def delete_contribution(self, contribution_id: str) -> APIResult:
        """Reject deletion because the current REST API exposes no DELETE method."""
        return APIResult(
            False,
            None,
            "GitHub Stars REST Contributions API does not provide DELETE; remove the contribution in the Stars web UI.",
        )

    # Legacy GraphQL surfaces --------------------------------------------
    async def create_link(self, link: str, platform: str) -> APIResult:
        return APIResult(
            **await self._execute_graphql(
                CREATE_LINK_MUTATION,
                {"link": link, "platform": platform},
                op="createLink",
            )
        )

    async def update_link(self, link_id: str, link: str, platform: str) -> APIResult:
        return APIResult(
            **await self._execute_graphql(
                UPDATE_LINK_MUTATION,
                {"id": link_id, "link": link, "platform": platform},
                op="updateLink",
            )
        )

    async def delete_link(self, link_id: str) -> APIResult:
        return APIResult(
            **await self._execute_graphql(
                DELETE_LINK_MUTATION, {"id": link_id}, op="deleteLink"
            )
        )

    async def get_user_data(self) -> APIResult:
        return APIResult(**await self._execute_graphql(USER_DATA_QUERY, op="userData"))

    async def get_stars(self, username: str) -> APIResult:
        return APIResult(
            **await self._execute_graphql(
                GET_STARS_QUERY, {"username": username}, op="getStars"
            )
        )

    async def get_user(self) -> APIResult:
        return APIResult(**await self._execute_graphql(USER_QUERY, op="getUser"))

    async def update_profile(self, data: dict[str, Any]) -> APIResult:
        return APIResult(
            **await self._execute_graphql(
                UPDATE_PROFILE_MUTATION, data, op="updateProfile"
            )
        )

    @retry(
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(3),
    )
    async def _execute_rest(
        self,
        method: str,
        *,
        path: str = "",
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        op: str,
    ) -> dict[str, Any]:
        url = f"{self.contributions_api_url}{path}"
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            resp = await client.request(method, url, params=params, json=json_body)
        duration_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code >= 400:
            try:
                error_body = resp.json()
                detail = (
                    error_body.get("message") or error_body.get("error") or resp.text
                )
            except (json.JSONDecodeError, AttributeError):
                detail = resp.text
            logger.warning(
                "stars_client.request_failed",
                op=op,
                http_status=resp.status_code,
                duration_ms=duration_ms,
                error_kind="http_error",
            )
            return {
                "ok": False,
                "data": None,
                "error": f"HTTP {resp.status_code}: {detail}",
            }

        if resp.status_code == 204:
            body: dict[str, Any] = {}
        else:
            try:
                body = resp.json()
            except json.JSONDecodeError:
                return {"ok": False, "data": None, "error": "Invalid JSON response"}

        logger.info(
            "stars_client.request_ok",
            op=op,
            http_status=resp.status_code,
            duration_ms=duration_ms,
        )
        return {"ok": True, "data": body, "error": None}

    @retry(
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(3),
    )
    async def _execute_graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        op: str | None = None,
    ) -> dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        op_name = op or "unknown"
        start = time.monotonic()
        async with httpx.AsyncClient(
            timeout=30, headers=self._headers, cookies=self._cookies
        ) as client:
            resp = await client.post(self.api_url, json=payload)
        duration_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code >= 400:
            logger.warning(
                "stars_client.request_failed",
                op=op_name,
                http_status=resp.status_code,
                duration_ms=duration_ms,
                error_kind="http_error",
            )
            return {
                "ok": False,
                "data": None,
                "error": f"HTTP {resp.status_code}: {resp.text}",
            }
        try:
            data = resp.json()
        except json.JSONDecodeError:
            return {"ok": False, "data": None, "error": "Invalid JSON response"}

        if data.get("errors"):
            return {
                "ok": False,
                "data": None,
                "error": data["errors"][0].get("message", "Unknown error"),
            }

        logger.info(
            "stars_client.request_ok",
            op=op_name,
            duration_ms=duration_ms,
            http_status=resp.status_code,
        )
        return {"ok": True, "data": data.get("data", {}), "error": None}
