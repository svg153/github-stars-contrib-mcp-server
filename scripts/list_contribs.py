"""Quick utility to list all contributions for a GitHub Stars public profile.

Usage:
    # Ensure virtualenv is active and env vars loaded (STARS_API_TOKEN)
    # Then run:
    #   PYTHONPATH=src python scripts/list_contribs.py svg153
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from github_stars_contrib_mcp.utils.stars_client import StarsClient


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def load_token() -> str | None:
    return os.getenv("STARS_API_TOKEN")


def build_client(token: str) -> StarsClient:
    return StarsClient(api_url="https://api-stars.github.com/", token=token)


def fetch_contribs(client: StarsClient, username: str) -> list[dict]:
    res = asyncio_run(client.get_stars(username))
    if not res.get("ok"):
        raise RuntimeError(str(res.get("error")))
    data = res.get("data") or {}
    profile = data.get("publicProfile")
    return (profile or {}).get("contributions", []) or []


def print_contribs(contribs: list[dict]) -> None:
    print(json.dumps(contribs, ensure_ascii=False, indent=2))


def main() -> int:
    if len(sys.argv) < 2:
        eprint("Usage: list_contribs.py <github_username>")
        return 2

    username = sys.argv[1]
    token = load_token()
    if not token:
        eprint("Error: STARS_API_TOKEN is not set in the environment.")
        return 1

    client = build_client(token)
    try:
        contributions = fetch_contribs(client, username)
    except Exception as exc:
        eprint(f"API error: {exc}")
        return 1

    if not contributions:
        print(
            json.dumps({"username": username, "contributions": []}, ensure_ascii=False)
        )
        return 0

    print_contribs(contributions)
    return 0


def asyncio_run(coro):
    return asyncio.run(coro)


if __name__ == "__main__":
    raise SystemExit(main())
