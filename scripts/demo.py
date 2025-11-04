#!/usr/bin/env python3
"""
Minimal local demo CLI to call MCP tools without an MCP client.

Usage examples:
  # Ensure STARS_API_TOKEN is set in your environment or .env
  python scripts/demo.py get-user-data
  python scripts/demo.py list-contributions
  python scripts/demo.py create-contributions --data '[{"title": "Test", "url": "https://example.com", "description": "Test description", "type": "BLOGPOST", "date": "2023-01-01T00:00:00Z"}]'
  python scripts/demo.py update-profile --data '{"name": "John Doe", "bio": "Updated bio"}'
  python scripts/demo.py delete-contribution --id "contribution-id"
"""

import argparse
import asyncio
import json
import sys

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.tools import (
    create_contributions,
    delete_contributions,
    get_user_data,
    update_profile,
)


async def ensure_client() -> None:
    await shared.initialize_stars_client()
    if shared.stars_client is None:
        print(
            "Stars client is not initialized. Set STARS_API_TOKEN in your environment or .env.",
            file=sys.stderr,
        )
        sys.exit(2)


async def cmd_get_user_data():
    await ensure_client()
    result = await get_user_data.get_user_data_impl()
    print(json.dumps(result, indent=2))


async def cmd_list_contributions():
    await ensure_client()
    result = await get_user_data.get_user_data_impl()

    if not result.get("success"):
        print(f"Error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)

    data = result.get("data", {})
    logged_user = data.get("loggedUser", {})
    contributions = logged_user.get("contributions", [])

    if not contributions:
        print("No contributions found.")
        return

    print(f"Found {len(contributions)} contributions:")
    print("-" * 80)

    for i, contrib in enumerate(contributions, 1):
        print(f"{i}. {contrib.get('title', 'N/A')}")
        print(f"   Type: {contrib.get('type', 'N/A')}")
        print(f"   Date: {contrib.get('date', 'N/A')}")
        print(f"   URL: {contrib.get('url', 'N/A')}")
        if contrib.get("description"):
            print(f"   Description: {contrib.get('description')}")
        print(f"   ID: {contrib.get('id', 'N/A')}")
        print()


async def cmd_create_contributions(data: str):
    await ensure_client()
    try:
        contributions_data = json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    result = await create_contributions.create_contributions_impl(contributions_data)
    print(json.dumps(result, indent=2))


async def cmd_delete_contribution(contribution_id: str):
    await ensure_client()
    result = await delete_contributions.delete_contribution_impl(contribution_id)
    print(json.dumps(result, indent=2))


async def cmd_update_profile(data: str):
    await ensure_client()
    try:
        profile_data = json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    result = await update_profile.update_profile_impl(profile_data)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Local demo CLI for GitHub Stars Contributions MCP tools"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("get-user-data", help="Get the currently logged user's data")

    sub.add_parser("list-contributions", help="List all user contributions")

    p3 = sub.add_parser("create-contributions", help="Create contributions")
    p3.add_argument(
        "--data",
        required=True,
        help='JSON array of contributions, e.g., [{"title": "Test", "url": "https://example.com", "description": "Test description", "type": "BLOGPOST", "date": "2023-01-01T00:00:00Z"}]',
    )

    p4 = sub.add_parser("delete-contribution", help="Delete a contribution by ID")
    p4.add_argument("--id", required=True, help="The ID of the contribution to delete")

    p5 = sub.add_parser("update-profile", help="Update user profile")
    p5.add_argument(
        "--data",
        required=True,
        help='JSON object with profile fields, e.g., {"name": "John Doe", "bio": "Updated bio"}',
    )

    args = parser.parse_args()

    if args.command == "get-user-data":
        asyncio.run(cmd_get_user_data())
    elif args.command == "list-contributions":
        asyncio.run(cmd_list_contributions())
    elif args.command == "create-contributions":
        asyncio.run(cmd_create_contributions(args.data))
    elif args.command == "delete-contribution":
        asyncio.run(cmd_delete_contribution(args.id))
    elif args.command == "update-profile":
        asyncio.run(cmd_update_profile(args.data))
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()
