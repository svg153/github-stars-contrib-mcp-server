#!/usr/bin/env python3
"""Minimal local CLI for exercising the GitHub Stars MCP implementations."""

import argparse
import asyncio
import json
import sys

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.tools import (
    create_contributions,
    list_contributions,
    update_contributions,
    update_profile,
)
from github_stars_contrib_mcp.tools.get_user_data import get_user_data_impl


async def ensure_client() -> None:
    await shared.initialize_stars_client()
    if shared.stars_client is None:
        print(
            "Stars client is not initialized. Set STARS_API_TOKEN.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def load_json(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


async def cmd_get_user_data() -> None:
    await ensure_client()
    print(json.dumps(await get_user_data_impl(), indent=2))


async def cmd_list_contributions(page: int) -> None:
    await ensure_client()
    print(json.dumps(await list_contributions.list_contributions_impl(page), indent=2))


async def cmd_create_contributions(data: str) -> None:
    await ensure_client()
    print(
        json.dumps(
            await create_contributions.create_contributions_impl(load_json(data)),
            indent=2,
        )
    )


async def cmd_upsert_contribution(client_id: str, data: str) -> None:
    await ensure_client()
    print(
        json.dumps(
            await update_contributions.upsert_contribution_impl(
                client_id,
                load_json(data),
            ),
            indent=2,
        )
    )


async def cmd_update_profile(data: str) -> None:
    await ensure_client()
    print(json.dumps(await update_profile.update_profile_impl(load_json(data)), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local demo CLI for GitHub Stars Contributions MCP tools"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("get-user-data", help="Get the logged user's profile data")

    list_parser = sub.add_parser(
        "list-contributions",
        help="List one authenticated REST contributions page",
    )
    list_parser.add_argument("--page", type=int, default=1)

    create_parser = sub.add_parser("create-contributions", help="Create contributions")
    create_parser.add_argument("--data", required=True, help="JSON contribution array")

    upsert_parser = sub.add_parser(
        "upsert-contribution",
        help="Idempotently create/replace one contribution by stable client ID",
    )
    upsert_parser.add_argument("--client-id", required=True)
    upsert_parser.add_argument("--data", required=True, help="Complete JSON contribution")

    profile_parser = sub.add_parser("update-profile", help="Update user profile")
    profile_parser.add_argument("--data", required=True, help="JSON profile object")

    args = parser.parse_args()
    if args.command == "get-user-data":
        asyncio.run(cmd_get_user_data())
    elif args.command == "list-contributions":
        asyncio.run(cmd_list_contributions(args.page))
    elif args.command == "create-contributions":
        asyncio.run(cmd_create_contributions(args.data))
    elif args.command == "upsert-contribution":
        asyncio.run(cmd_upsert_contribution(args.client_id, args.data))
    elif args.command == "update-profile":
        asyncio.run(cmd_update_profile(args.data))


if __name__ == "__main__":
    main()
