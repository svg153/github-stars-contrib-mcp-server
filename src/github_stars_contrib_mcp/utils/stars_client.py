"""GitHub Stars API client with REST Contributions and observable legacy GraphQL."""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ..observability import MetricsCollector, get_tracer
from ..resilience import CircuitBreakerException, circuit_breaker_registry
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
            "User-Agent": "github-stars-contrib-mcp-server/0.3.0",
            "Accept": "application/json",
        }
        self._cookies = {"token": self.token}
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"
        self.breaker = circuit_breaker_registry.get_or_create(
            "stars_api", failure_threshold=5, recovery_timeout=60
        )
        self.tracer = get_tracer()

    async def validate_token(self) -> APIResult:
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
        for item in items:
            MetricsCollector.record_contribution_created(
                str(item.get("type") or "UNKNOWN")
            )
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
        contribution = (
            contributions[0]
            if isinstance(contributions, list) and contributions
            else contributions
            if not isinstance(contributions, list)
            else None
        )
        MetricsCollector.record_contribution_updated(str(data.get("type") or "UNKNOWN"))
        return APIResult(True, {"upsertContribution": contribution})

    async def update_contribution(
        self, contribution_id: str, data: dict[str, Any]
    ) -> APIResult:
        return APIResult(
            False,
            None,
            "update_contribution is retired: use upsert_contribution with a stable caller-controlled client ID and a complete payload",
        )

    async def delete_contribution(self, contribution_id: str) -> APIResult:
        return APIResult(
            False,
            None,
            "GitHub Stars REST Contributions API does not provide DELETE; remove the contribution in the Stars web UI.",
        )

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
        wait=wait_exponential_jitter(initial=0.5, max=8, jitter=1),
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
        endpoint = f"/contributions{path}"
        request_size = len(json.dumps(json_body or {}))
        with self.tracer.span(
            f"rest_{op}", {"operation": op, "http.method": method}
        ) as span:
            try:
                return await self.breaker.async_call(
                    self._make_rest_request,
                    method,
                    path,
                    params,
                    json_body,
                    op,
                    endpoint,
                    request_size,
                    span,
                )
            except CircuitBreakerException as exc:
                MetricsCollector.record_error("CIRCUIT_BREAKER_OPEN", endpoint)
                logger.error("stars_client.circuit_breaker_open", op=op, error=str(exc))
                return {
                    "ok": False,
                    "data": None,
                    "error": "Service temporarily unavailable (circuit breaker open)",
                }

    async def _make_rest_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        json_body: dict[str, Any] | None,
        op: str,
        endpoint: str,
        request_size: int,
        span: Any,
    ) -> dict[str, Any]:
        url = f"{self.contributions_api_url}{path}"
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            resp = await client.request(method, url, params=params, json=json_body)
        duration_sec = time.monotonic() - start
        duration_ms = int(duration_sec * 1000)
        response_size = len(resp.text or "")
        MetricsCollector.record_request(
            method,
            endpoint,
            resp.status_code,
            duration_sec,
            request_size,
            response_size,
        )
        self.tracer.add_event(
            span,
            "http_response",
            {"status": resp.status_code, "duration_ms": duration_ms},
        )

        if resp.status_code >= 400:
            try:
                error_body = resp.json()
                detail = (
                    error_body.get("message") or error_body.get("error") or resp.text
                )
            except (json.JSONDecodeError, AttributeError):
                detail = resp.text
            MetricsCollector.record_error(f"HTTP_{resp.status_code}", endpoint)
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
                MetricsCollector.record_error("JSON_DECODE_ERROR", endpoint)
                return {"ok": False, "data": None, "error": "Invalid JSON response"}

        logger.info(
            "stars_client.request_ok",
            op=op,
            http_status=resp.status_code,
            duration_ms=duration_ms,
        )
        return {"ok": True, "data": body, "error": None}

    @retry(
        wait=wait_exponential_jitter(initial=0.5, max=8, jitter=1),
        stop=stop_after_attempt(3),
    )
    async def _execute_graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        op: str | None = None,
    ) -> dict[str, Any]:
        op_name = op or "unknown"
        payload = {"query": query, "variables": variables or {}}
        endpoint = f"/graphql/{op_name}"
        request_size = len(json.dumps(payload["variables"]))
        with self.tracer.span(f"graphql_{op_name}", {"operation": op_name}) as span:
            try:
                return await self.breaker.async_call(
                    self._make_graphql_request,
                    payload,
                    op_name,
                    endpoint,
                    request_size,
                    span,
                )
            except CircuitBreakerException as exc:
                MetricsCollector.record_error("CIRCUIT_BREAKER_OPEN", endpoint)
                logger.error(
                    "stars_client.circuit_breaker_open", op=op_name, error=str(exc)
                )
                return {
                    "ok": False,
                    "data": None,
                    "error": "Service temporarily unavailable (circuit breaker open)",
                }

    async def _make_graphql_request(
        self,
        payload: dict[str, Any],
        op_name: str,
        endpoint: str,
        request_size: int,
        span: Any,
    ) -> dict[str, Any]:
        start = time.monotonic()
        async with httpx.AsyncClient(
            timeout=30, headers=self._headers, cookies=self._cookies
        ) as client:
            resp = await client.post(self.api_url, json=payload)
        duration_sec = time.monotonic() - start
        duration_ms = int(duration_sec * 1000)
        response_size = len(resp.text or "")
        MetricsCollector.record_request(
            "POST",
            endpoint,
            resp.status_code,
            duration_sec,
            request_size,
            response_size,
        )
        self.tracer.add_event(
            span,
            "http_response",
            {"status": resp.status_code, "duration_ms": duration_ms},
        )

        if resp.status_code >= 400:
            MetricsCollector.record_error(f"HTTP_{resp.status_code}", endpoint)
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
            MetricsCollector.record_error("JSON_DECODE_ERROR", endpoint)
            return {"ok": False, "data": None, "error": "Invalid JSON response"}

        if data.get("errors"):
            MetricsCollector.record_error("GRAPHQL_ERROR", endpoint)
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
