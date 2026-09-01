# Agents integration guide

Source of truth: `src/github_stars_contrib_mcp/tools/*` and `src/github_stars_contrib_mcp/utils/*`.

## Protocol/API contract

- MCP server: official Python MCP SDK 2.x (`MCPServer`), protocol revision `2026-07-28`.
- Contributions: REST `https://stars.github.com/api/contributions`.
- Profile/link/public Stars operations: keep GraphQL only where the reviewed migration provides no documented REST replacement.

## Contribution tools

- `list_contributions(page=1)` — authenticated REST GET with pagination.
- `create_contribution(data)` — REST POST one item.
- `create_contributions(data)` — REST POST batch.
- `upsert_contribution(client_id, data)` — REST PUT by stable caller-controlled client ID; pass the complete contribution.

Never translate a legacy GraphQL contribution/server ID into a REST `client_id`. Do not invent a contribution DELETE operation; deletion is a Stars web UI operation.

Example agent call:

```text
upsert_contribution(client_id="post:example", data={title, url, type, date, description})
-> {"success": true, "data": {...}, "error": null}
```

## Links and platform normalization

Valid platforms: `TWITTER`, `MEDIUM`, `LINKEDIN`, `README`, `STACK_OVERFLOW`, `DEV_TO`, `MASTODON`, `OTHER`. Normalize compatibility aliases before calling GraphQL: `GITHUB -> README`, `WEBSITE -> OTHER`.

## Transport

- Prefer `stdio` locally and `streamable-http` for deployed servers.
- `http` is a compatibility alias for `streamable-http`.
- SSE is legacy-only.
- Transport options belong on `MCPServer.run()`.

## Configuration

- `STARS_API_TOKEN`
- `STARS_API_URL` and `STARS_CONTRIBUTIONS_API_URL`
- `STARS_AUTH_MODE=both|bearer|cookie`
- `STARS_USER_AGENT`
- `LOG_LEVEL`
- `MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT`, `MCP_PATH`

## Reliability rules

- Retry only transient Stars responses (`429` and `5xx`); do not retry permanent `4xx` failures.
- Never log credentials. DEBUG GraphQL variable logging must redact token/secret/password/auth/cookie keys.
- Keep contribution behavior aligned with `ahmadawais/github-stars-contributions` rather than retired GraphQL mutations.
- New contribution writes are REST-only.
- Do not reintroduce `FastMCP`; use the official MCP Python SDK 2.x.
- Unit CI must not depend on `STARS_API_TOKEN`; integration tests belong in the dedicated integration workflow.
