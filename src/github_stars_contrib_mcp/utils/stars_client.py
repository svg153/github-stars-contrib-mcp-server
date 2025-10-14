"""Minimal GraphQL client for GitHub Stars Contributions API."""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

CREATE_CONTRIBUTIONS_MUTATION = (
    """
    mutation($data: [ContributionInput!]!) {
      createContributions(data: $data) { id }
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
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    async def create_contributions(self, items: list[dict]) -> StarsAPIResult:
        payload = {"query": CREATE_CONTRIBUTIONS_MUTATION, "variables": {"data": items}}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.api_url, headers=self._headers, json=payload)
            if resp.status_code >= 400:
                return StarsAPIResult(False, [], f"HTTP {resp.status_code}: {resp.text}")
            try:
                data = resp.json()
            except json.JSONDecodeError:
                return StarsAPIResult(False, [], "Invalid JSON response")

            if "errors" in data and data["errors"]:
                return StarsAPIResult(False, [], data["errors"][0].get("message", "Unknown error"))

            edges = data.get("data", {}).get("createContributions", [])
            ids = [edge.get("id") for edge in edges if edge and edge.get("id")]
            return StarsAPIResult(True, ids)

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    async def get_user_data(self) -> dict:
        """Fetch the logged user's data from the Stars API.

        Returns a dict with keys: ok (bool), data (dict | None), error (str | None).
        """
        payload = {"query": USER_DATA_QUERY, "variables": {}}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.api_url, headers=self._headers, json=payload)
            if resp.status_code >= 400:
                return {"ok": False, "data": None, "error": f"HTTP {resp.status_code}: {resp.text}"}
            try:
                data = resp.json()
            except json.JSONDecodeError:
                return {"ok": False, "data": None, "error": "Invalid JSON response"}

            if "errors" in data and data["errors"]:
                return {"ok": False, "data": None, "error": data["errors"][0].get("message", "Unknown error")}

            return {"ok": True, "data": data.get("data", {}), "error": None}
