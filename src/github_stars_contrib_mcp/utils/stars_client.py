"""Minimal GraphQL client for GitHub Stars Contributions API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# GraphQL Queries and Mutations
CREATE_CONTRIBUTIONS_MUTATION = (
    """
    mutation($data: [ContributionInput!]!) {
      createContributions(data: $data) { id }
    }
    """
    .strip()
)

CREATE_CONTRIBUTION_MUTATION = (
    """
    mutation CreateContribution($type: ContributionType, $date: GraphQLDateTime, $title: String, $url: URL, $description: String!) {
      createContribution(
        data: {type: $type, date: $date, title: $title, url: $url, description: $description}
      ) {
        id
        type
        date
        title
        url
        description
        __typename
      }
        }
    """
    .strip()
)

UPDATE_CONTRIBUTION_MUTATION = (
    """
        mutation($id: String!, $data: ContributionInput!) {
      updateContribution(id: $id, data: $data) {
        id type date title url description __typename
      }
    }
    """
    .strip()
)

DELETE_CONTRIBUTION_MUTATION = (
    """
    mutation($id: String!) {
      deleteContribution(id: $id) {
        id __typename
      }
    }
    """
    .strip()
)

CREATE_LINK_MUTATION = (
    """
    mutation CreateLink($link: URL, $platform: PlatformType) {
      createLink(data: {link: $link, platform: $platform}) {
        id
        link
        platform
        __typename
      }
        }
    """
    .strip()
)

UPDATE_LINK_MUTATION = (
    """
    mutation UpdateLink($id: String!, $link: URL, $platform: PlatformType) {
      updateLink(id: $id, data: {link: $link, platform: $platform}) {
        id
        link
        platform
        __typename
      }
    }
    """
    .strip()
)

DELETE_LINK_MUTATION = (
    """
    mutation DeleteLink($id: String!) {
      deleteLink(id: $id) {
        id
        __typename
      }
    }
    """
    .strip()
)

USER_DATA_QUERY = (
    """
    query UserData {
        loggedUser {
            id
            username
            email
            nominee {
                status
                avatar
                name
                bio
                country
                birthdate
                reason
                jobTitle
                company
                phoneNumber
                address
                state
                city
                zipcode
                links { id link platform __typename }
                contributions { id type date title url description __typename }
                __typename
            }
            __typename
        }
    }
    """
    .strip()
)

GET_STARS_QUERY = (
    """
    query GetStars($username: String!) {
      publicProfile(username: $username) {
        id
        username
        name
        avatar
        bio
        status
        country
        links {
          id
          link
          platform
          __typename
        }
        contributions {
          id
          type
          date
          title
          url
          description
          __typename
        }
        __typename
      }
    }
    """
    .strip()
)

USER_QUERY = (
    """
    query User {
      loggedUser {
        id
        username
        avatar
        nominee {
          status
          __typename
        }
        nominations {
          id
          nominee {
            id
            username
            name
            __typename
          }
          content
          __typename
        }
        __typename
      }
    }
    """
    .strip()
)

UPDATE_PROFILE_MUTATION = (
    """
    mutation UpdateProfile($avatar: String, $name: String, $bio: String, $country: String, $birthdate: GraphQLDateTime, $reason: String, $jobTitle: String, $company: String, $phoneNumber: String, $address: String, $state: String, $city: String, $zipcode: String) {
      updateProfile(
        data: {avatar: $avatar, name: $name, bio: $bio, country: $country, birthdate: $birthdate, reason: $reason, jobTitle: $jobTitle, company: $company, phoneNumber: $phoneNumber, address: $address, state: $state, city: $city, zipcode: $zipcode}
      ) {
        id
        __typename
      }
    }
    """
    .strip()
)


@dataclass
class StarsAPIResult:
    ok: bool
    ids: list[str]
    error: str | None = None


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
    async def create_contributions(self, items: list[dict[str, Any]]) -> StarsAPIResult:
        """Create multiple contributions.

        Args:
            items: List of contribution data dicts.

        Returns:
            StarsAPIResult with ok, ids, error.
        """
        result = await self._execute_graphql(CREATE_CONTRIBUTIONS_MUTATION, {"data": items})
        if not result["ok"]:
            return StarsAPIResult(False, [], result["error"])

        edges = result["data"].get("createContributions", [])
        ids = [edge.get("id") for edge in edges if edge and edge.get("id")]
        return StarsAPIResult(True, ids)

    async def create_contribution(self, type: str, date: str, title: str, url: str, description: str) -> dict[str, Any]:
        """Create a single contribution.

        Args:
            type: Contribution type.
            date: ISO date string.
            title: Contribution title.
            url: Contribution URL.
            description: Contribution description.

        Returns:
            Dict with ok, data, error.
        """
        variables = {
            "type": type,
            "date": date,
            "title": title,
            "url": url,
            "description": description
        }
        return await self._execute_graphql(CREATE_CONTRIBUTION_MUTATION, variables)

    async def update_contribution(self, contribution_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a contribution.

        Args:
            contribution_id: ID of the contribution to update.
            data: Update data dict.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(UPDATE_CONTRIBUTION_MUTATION, {"id": contribution_id, "data": data})

    async def delete_contribution(self, contribution_id: str) -> dict[str, Any]:
        """Delete a contribution.

        Args:
            contribution_id: ID of the contribution to delete.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(DELETE_CONTRIBUTION_MUTATION, {"id": contribution_id})

    # Link methods
    async def create_link(self, link: str, platform: str) -> dict[str, Any]:
        """Create a link.

        Args:
            link: Link URL.
            platform: Platform type.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(CREATE_LINK_MUTATION, {"link": link, "platform": platform})

    async def update_link(self, link_id: str, link: str, platform: str) -> dict[str, Any]:
        """Update a link.

        Args:
            link_id: ID of the link to update.
            link: New link URL.
            platform: Platform type.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(UPDATE_LINK_MUTATION, {"id": link_id, "link": link, "platform": platform})

    async def delete_link(self, link_id: str) -> dict[str, Any]:
        """Delete a link.

        Args:
            link_id: ID of the link to delete.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(DELETE_LINK_MUTATION, {"id": link_id})

    # Profile methods
    async def get_user_data(self) -> dict[str, Any]:
        """Fetch the logged user's data from the Stars API.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(USER_DATA_QUERY)

    async def get_stars(self, username: str) -> dict[str, Any]:
        """Fetch the public profile stars/contributions for a user from the Stars API.

        Args:
            username: GitHub username.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(GET_STARS_QUERY, {"username": username})

    async def get_user(self) -> dict[str, Any]:
        """Fetch the logged user's data including nominations from the Stars API.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(USER_QUERY)

    async def update_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update the user profile.

        Args:
            data: Profile update data dict.

        Returns:
            Dict with ok, data, error.
        """
        return await self._execute_graphql(UPDATE_PROFILE_MUTATION, {"data": data})

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
