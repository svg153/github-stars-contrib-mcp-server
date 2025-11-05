"""GitHub Stars API client."""
# isort: skip_file

from typing import Any
import json
import time

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
)
import structlog

from .models import APIResult
from .queries import (
    CREATE_CONTRIBUTION_MUTATION,
    CREATE_CONTRIBUTIONS_MUTATION,
    CREATE_LINK_MUTATION,
    DELETE_CONTRIBUTION_MUTATION,
    DELETE_LINK_MUTATION,
    GET_STARS_QUERY,
    UPDATE_CONTRIBUTION_MUTATION,
    UPDATE_LINK_MUTATION,
    UPDATE_PROFILE_MUTATION,
    USER_DATA_QUERY,
    USER_QUERY,
)
from ..resilience import circuit_breaker_registry, CircuitBreakerException
from ..observability import MetricsCollector, get_tracer

logger = structlog.get_logger(__name__)


class StarsClient:
    def __init__(self, api_url: str, token: str) -> None:
        self.api_url = api_url.rstrip("/") + "/"
        self.token = token
        self._headers = {
            "Content-Type": "application/json",
            # Add browser-like headers; some endpoints may validate origin/referrer
            "Origin": "https://stars.github.com",
            "Referer": "https://stars.github.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
            "Accept": "*/*",
        }
        self._cookies = {"token": self.token}
        # Also include Authorization as a fallback if server supports bearer tokens
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"

        # Initialize circuit breaker for API calls
        self.breaker = circuit_breaker_registry.get_or_create(
            "stars_api",
            failure_threshold=5,
            recovery_timeout=60,
        )
        # Initialize tracer
        self.tracer = get_tracer()

    # Contribution methods
    async def create_contributions(self, items: list[dict[str, Any]]) -> APIResult:
        """Create multiple contributions.

        Args:
            items: List of contribution data dicts.

        Returns:
            APIResult with ok, data, error. data contains 'ids' key with list of created IDs.
        """
        result = await self._execute_graphql(
            CREATE_CONTRIBUTIONS_MUTATION, {"data": items}, op="createContributions"
        )
        if not result["ok"]:
            return APIResult(False, None, result["error"])

        edges = result["data"].get("createContributions", [])
        ids = [edge.get("id") for edge in edges if edge and edge.get("id")]
        return APIResult(True, {"ids": ids})

    async def create_contribution(
        self, type: str, date: str, title: str, url: str, description: str
    ) -> APIResult:
        """Create a single contribution.

        Args:
            type: Contribution type.
            date: ISO date string.
            title: Contribution title.
            url: Contribution URL.
            description: Contribution description.

        Returns:
            APIResult with ok, data, error.
        """
        variables = {
            "data": {
                "type": type,
                "date": date,
                "title": title,
                "url": url,
                "description": description,
            }
        }
        return APIResult(
            **await self._execute_graphql(
                CREATE_CONTRIBUTION_MUTATION, variables, op="createContribution"
            )
        )

    async def update_contribution(
        self, contribution_id: str, data: dict[str, Any]
    ) -> APIResult:
        """Update a contribution.

        Args:
            contribution_id: ID of the contribution to update.
            data: Update data dict.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(
            **await self._execute_graphql(
                UPDATE_CONTRIBUTION_MUTATION,
                {"id": contribution_id, "data": data},
                op="updateContribution",
            )
        )

    async def delete_contribution(self, contribution_id: str) -> APIResult:
        """Delete a contribution.

        Args:
            contribution_id: ID of the contribution to delete.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(
            **await self._execute_graphql(
                DELETE_CONTRIBUTION_MUTATION,
                {"id": contribution_id},
                op="deleteContribution",
            )
        )

    # Link methods
    async def create_link(self, link: str, platform: str) -> APIResult:
        """Create a link.

        Args:
            link: Link URL.
            platform: Platform type.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(
            **await self._execute_graphql(
                CREATE_LINK_MUTATION,
                {"link": link, "platform": platform},
                op="createLink",
            )
        )

    async def update_link(self, link_id: str, link: str, platform: str) -> APIResult:
        """Update a link.

        Args:
            link_id: ID of the link to update.
            link: New link URL.
            platform: Platform type.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(
            **await self._execute_graphql(
                UPDATE_LINK_MUTATION,
                {"id": link_id, "link": link, "platform": platform},
                op="updateLink",
            )
        )

    async def delete_link(self, link_id: str) -> APIResult:
        """Delete a link.

        Args:
            link_id: ID of the link to delete.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(
            **await self._execute_graphql(
                DELETE_LINK_MUTATION, {"id": link_id}, op="deleteLink"
            )
        )

    # Profile methods
    async def get_user_data(self) -> APIResult:
        """Fetch the logged user's data from the Stars API.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(USER_DATA_QUERY, op="userData"))

    async def get_stars(self, username: str) -> APIResult:
        """Fetch the public profile stars/contributions for a user from the Stars API.

        Args:
            username: GitHub username.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(
            **await self._execute_graphql(
                GET_STARS_QUERY, {"username": username}, op="getStars"
            )
        )

    async def get_user(self) -> APIResult:
        """Fetch the logged user's data including nominations from the Stars API.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(USER_QUERY, op="getUser"))

    async def update_profile(self, data: dict[str, Any]) -> APIResult:
        """Update the user profile.

        Args:
            data: Profile update data dict.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(
            **await self._execute_graphql(
                UPDATE_PROFILE_MUTATION, data, op="updateProfile"
            )
        )

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
        """Execute a GraphQL query/mutation and return the response data or error.

        Returns a dict with keys: ok (bool), data (dict | None), error (str | None).
        Uses circuit breaker to prevent cascading failures.
        Traces requests and records metrics.
        """
        op_name = op or "unknown"
        payload = {"query": query, "variables": variables or {}}
        request_size = (
            len(json.dumps(payload.get("variables", {})))
            if payload.get("variables")
            else 0
        )

        # Start tracing span
        with self.tracer.span(
            f"graphql_{op_name}",
            {
                "operation": op_name,
                "request_size": request_size,
            },
        ) as span:
            try:
                # Execute through circuit breaker
                result = await self.breaker.acall(
                    self._make_graphql_request,
                    payload,
                    op_name,
                    request_size,
                    span,
                )
                return result
            except CircuitBreakerException as e:
                logger.error(
                    "stars_client.circuit_breaker_open",
                    op=op_name,
                    error=str(e),
                )
                MetricsCollector.record_error(
                    "CIRCUIT_BREAKER_OPEN", f"/graphql/{op_name}"
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
        request_size: int,
        span: Any,
    ) -> dict[str, Any]:
        """Make actual GraphQL request (called through circuit breaker)."""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=30, headers=self._headers, cookies=self._cookies
            ) as client:
                resp = await client.post(self.api_url, json=payload)
                duration_sec = time.monotonic() - start
                duration_ms = int(duration_sec * 1000)
                resp_text = resp.text
                response_size = len(resp_text) if resp_text else 0

                # Record metrics
                MetricsCollector.record_request(
                    method="POST",
                    endpoint=f"/graphql/{op_name}",
                    status=resp.status_code,
                    latency_sec=duration_sec,
                    req_size=request_size,
                    resp_size=response_size,
                )

                # Add event to span
                self.tracer.add_event(
                    span,
                    "http_response",
                    {
                        "status": resp.status_code,
                        "duration_ms": duration_ms,
                    },
                )

                if resp.status_code >= 400:
                    logger.warning(
                        "stars_client.request_failed",
                        op=op_name,
                        http_status=resp.status_code,
                        duration_ms=duration_ms,
                        request_size=request_size,
                        response_size=response_size,
                        error_kind="http_error",
                    )
                    MetricsCollector.record_error(
                        f"HTTP_{resp.status_code}",
                        f"/graphql/{op_name}",
                    )
                    return {
                        "ok": False,
                        "data": None,
                        "error": f"HTTP {resp.status_code}: {resp_text}",
                    }

                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    logger.warning(
                        "stars_client.request_failed",
                        op=op_name,
                        duration_ms=duration_ms,
                        request_size=request_size,
                        response_size=response_size,
                        error_kind="json_error",
                    )
                    MetricsCollector.record_error(
                        "JSON_DECODE_ERROR",
                        f"/graphql/{op_name}",
                    )
                    return {
                        "ok": False,
                        "data": None,
                        "error": "Invalid JSON response",
                    }

                if "errors" in data and data["errors"]:
                    logger.warning(
                        "stars_client.request_failed",
                        op=op_name,
                        duration_ms=duration_ms,
                        request_size=request_size,
                        response_size=response_size,
                        error_kind="graphql_error",
                    )
                    MetricsCollector.record_error(
                        "GRAPHQL_ERROR",
                        f"/graphql/{op_name}",
                    )
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
                    request_size=request_size,
                    response_size=response_size,
                )

                # Add success event to span
                self.tracer.add_event(
                    span,
                    "graphql_success",
                    {"has_data": "data" in data},
                )

                return {"ok": True, "data": data.get("data", {}), "error": None}
        except Exception as e:
            logger.error(
                "stars_client.request_exception",
                op=op_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            MetricsCollector.record_error(
                type(e).__name__,
                f"/graphql/{op_name}",
            )
            raise
