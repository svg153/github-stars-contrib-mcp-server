# Agents integration guide

Minimal, non-duplicative reference for building agents for this server (contributions API).

Source of truth: see `src/github_stars_contrib_mcp/tools/*` and `src/github_stars_contrib_mcp/utils/*`.

## What this server does

- Exposes MCP tools to create GitHub Stars contributions via GraphQL

## Capabilities

- tools (list/call)

## Tools overview

- create_contributions
  - input: { data: ContributionInput[] }
  - output: { success: boolean, ids?: string[], error?: any }
- create_link
  - input: { link: string, platform: string }
  - output: { success: boolean, data?: object, error?: any }
- update_link
  - input: { id: string, data: LinkUpdateInput }
  - output: { success: boolean, data?: object, error?: any }
- delete_link
  - input: { id: string }
  - output: { success: boolean, data?: object, error?: any }
- update_contribution
  - input: { id: string, data: ContributionUpdateInput }
  - output: { success: boolean, data?: object, error?: any }
- delete_contribution
  - input: { id: string }
  - output: { success: boolean, data?: object, error?: any }
- get_user_data
  - input: none
  - output: { success: boolean, data?: object, error?: any }
- get_user
  - input: none
  - output: { success: boolean, data?: object, error?: any }
- get_stars
  - input: { username: string }
  - output: { success: boolean, data?: object, error?: any }
- update_profile
  - input: { data: ProfileUpdateInput }
  - output: { success: boolean, data?: object, error?: any }

ContributionInput fields: title, url, description?, type, date (ISO)

## Transport and invocation

- JSON-RPC 2.0 via MCP (Streamable HTTP)
- Discovery: tools/list
- Calls: tools/call

## Configuration

Environment variables:

- STARS_API_TOKEN (required to call remote API)
- LOG_LEVEL (default: INFO)

## How to run locally

- Setup virtual environment: `make venv` (creates `.venv` directory)
- Activate virtual environment: `source .venv/bin/activate`
- Install: `pip install -e .[dev]`
- Start server: `python -m github_stars_contrib_mcp.server`

Server binds to 127.0.0.1:8766 by default (SSE transport).

## Safety and limits

- Auth: requires the GitHub Stars API token for mutations
- Errors: HTTP and GraphQL errors are surfaced in the `error` field

## References

- FastMCP: tool registration via `@mcp.tool` decorator
- See `src/github_stars_contrib_mcp/tools/create_contributions.py` and `src/github_stars_contrib_mcp/tools/get_user_data.py` for canonical tool definitions
