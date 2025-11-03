"""GitHub Stars API client."""
# isort: skip_file

from typing import Any
import json

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

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

    # Contribution methods
    async def create_contributions(self, items: list[dict[str, Any]]) -> APIResult:
        """Create multiple contributions.

        Args:
            items: List of contribution data dicts.

        Returns:
            APIResult with ok, data, error. data contains 'ids' key with list of created IDs.
        """
        result = await self._execute_graphql(CREATE_CONTRIBUTIONS_MUTATION, {"data": items})
        if not result["ok"]:
            return APIResult(False, None, result["error"])

        edges = result["data"].get("createContributions", [])
        ids = [edge.get("id") for edge in edges if edge and edge.get("id")]
        return APIResult(True, {"ids": ids})

    async def create_contribution(self, type: str, date: str, title: str, url: str, description: str) -> APIResult:
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
        return APIResult(**await self._execute_graphql(CREATE_CONTRIBUTION_MUTATION, variables))

    async def update_contribution(self, contribution_id: str, data: dict[str, Any]) -> APIResult:
        """Update a contribution.

        Args:
            contribution_id: ID of the contribution to update.
            data: Update data dict.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(UPDATE_CONTRIBUTION_MUTATION, {"id": contribution_id, "data": data}))

    async def delete_contribution(self, contribution_id: str) -> APIResult:
        """Delete a contribution.

        Args:
            contribution_id: ID of the contribution to delete.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(DELETE_CONTRIBUTION_MUTATION, {"id": contribution_id}))

    # Link methods
    async def create_link(self, link: str, platform: str) -> APIResult:
        """Create a link.

        Args:
            link: Link URL.
            platform: Platform type.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(CREATE_LINK_MUTATION, {"link": link, "platform": platform}))

    async def update_link(self, link_id: str, link: str, platform: str) -> APIResult:
        """Update a link.

        Args:
            link_id: ID of the link to update.
            link: New link URL.
            platform: Platform type.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(UPDATE_LINK_MUTATION, {"id": link_id, "link": link, "platform": platform}))

    async def delete_link(self, link_id: str) -> APIResult:
        """Delete a link.

        Args:
            link_id: ID of the link to delete.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(DELETE_LINK_MUTATION, {"id": link_id}))

    # Profile methods
    async def get_user_data(self) -> APIResult:
        """Fetch the logged user's data from the Stars API.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(USER_DATA_QUERY))

    async def get_stars(self, username: str) -> APIResult:
        """Fetch the public profile stars/contributions for a user from the Stars API.

        Args:
            username: GitHub username.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(GET_STARS_QUERY, {"username": username}))

    async def get_user(self) -> APIResult:
        """Fetch the logged user's data including nominations from the Stars API.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(USER_QUERY))

    async def update_profile(self, data: dict[str, Any]) -> APIResult:
        """Update the user profile.

        Args:
            data: Profile update data dict.

        Returns:
            APIResult with ok, data, error.
        """
        return APIResult(**await self._execute_graphql(UPDATE_PROFILE_MUTATION, data))

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    async def _execute_graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query/mutation and return the response data or error.

        Returns a dict with keys: ok (bool), data (dict | None), error (str | None).
        """
        payload = {"query": query, "variables": variables or {}}
        async with httpx.AsyncClient(timeout=30, headers=self._headers, cookies=self._cookies) as client:
            resp = await client.post(self.api_url, json=payload)
            if resp.status_code >= 400:
                return {"ok": False, "data": None, "error": f"HTTP {resp.status_code}: {resp.text}"}
            try:
                data = resp.json()
            except json.JSONDecodeError:
                return {"ok": False, "data": None, "error": "Invalid JSON response"}

            if "errors" in data and data["errors"]:
                return {"ok": False, "data": None, "error": data["errors"][0].get("message", "Unknown error")}

            return {"ok": True, "data": data.get("data", {}), "error": None}
