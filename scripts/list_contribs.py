"""List authenticated GitHub Stars contributions through the REST API."""

from __future__ import annotations

import asyncio
import json
import os
import sys

from github_stars_contrib_mcp.utils.stars_client import StarsClient


def build_client(token: str) -> StarsClient:
    return StarsClient(
        api_url=os.getenv("STARS_API_URL", "https://api-stars.github.com/"),
        contributions_api_url=os.getenv(
            "STARS_CONTRIBUTIONS_API_URL",
            "https://stars.github.com/api/contributions",
        ),
        token=token,
    )


async def fetch_all(client: StarsClient) -> list[dict]:
    contributions: list[dict] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        result = await client.list_contributions(page)
        if not result.ok:
            raise RuntimeError(result.error or "Stars API error")
        body = result.data or {}
        contributions.extend(body.get("data", []))
        pagination = body.get("pagination", {})
        total_pages = int(pagination.get("totalPages", page))
        page += 1
    return contributions


def main() -> int:
    token = os.getenv("STARS_API_TOKEN")
    if not token:
        print("Error: STARS_API_TOKEN is not set.", file=sys.stderr)
        return 1
    try:
        contributions = asyncio.run(fetch_all(build_client(token)))
    except Exception as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(contributions, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
