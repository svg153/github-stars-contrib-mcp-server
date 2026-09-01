# Agents integration guide

Source of truth: `src/github_stars_contrib_mcp/tools/*` and `src/github_stars_contrib_mcp/utils/*`.

## Protocol/API contract

- MCP server: official Python MCP SDK 2.x (`MCPServer`), protocol revision `2026-07-28` with SDK-managed compatibility for older clients.
- Contributions: REST `https://stars.github.com/api/contributions`.
- Profile/link/public Stars operations: keep the existing GraphQL path only where the reviewed migration provides no documented REST replacement.

## Contribution tools

- `list_contributions(page=1)` — authenticated REST GET with pagination.
- `create_contribution(data)` — REST POST one item.
- `create_contributions(data)` — REST POST batch.
- `upsert_contribution(client_id, data)` — REST PUT by stable caller-controlled client ID; pass the complete contribution.

Never translate a legacy GraphQL contribution/server ID into a REST `client_id` automatically. They have different semantics and doing so can create a duplicate record.

Do **not** invent or call a contribution delete operation: GitHub's current REST Contributions API does not provide DELETE. Deletion is a Stars web UI operation.

## Transport

- Prefer `stdio` locally and `streamable-http` for deployed servers.
- `http` is a compatibility alias for `streamable-http`.
- SSE is legacy-only.
- Transport options belong on `MCPServer.run()`, following the MCP SDK 2.x contract.

## Configuration

- `STARS_API_TOKEN`
- `STARS_API_URL` (remaining GraphQL surfaces)
- `STARS_CONTRIBUTIONS_API_URL` (current REST Contributions URL)
- `LOG_LEVEL`
- `MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT`, `MCP_PATH`

## Engineering notes

- Keep contribution behavior aligned with the upstream `ahmadawais/github-stars-contributions` REST implementation instead of reverse-engineering retired GraphQL mutations.
- Keep transport concerns inside `StarsClient` and adapters; tools depend on application/domain boundaries.
- New contribution writes are REST-only.
- Do not reintroduce `FastMCP`; this repository is on the official MCP Python SDK 2.x `MCPServer` API.
- Run tests, Ruff and type checking before merge.
