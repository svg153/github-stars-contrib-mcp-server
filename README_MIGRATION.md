# 0.2.0 migration notes

This release aligns the server with the GitHub Stars Contributions REST migration and the official MCP Python SDK 2.x line.

## What changes for MCP clients

- MCP protocol support moves to the official SDK 2.x (`MCPServer`) and protocol revision `2026-07-28`.
- `update_contribution` is replaced by `upsert_contribution(client_id, data)`.
- `delete_contribution` is removed from MCP discovery because the REST API has no DELETE method.
- `list_contributions(page)` is now available over REST.

## Important ID migration rule

A REST `client_id` is caller-controlled and is not the same concept as the legacy GraphQL/server-generated contribution ID. Existing server IDs must not be silently reused as PUT client IDs. Choose a deterministic new client ID for records you want to manage idempotently going forward.

## API split

- Contribution GET/POST/PUT: `STARS_CONTRIBUTIONS_API_URL`, default `https://stars.github.com/api/contributions`.
- Profile/link/public-profile operations: existing `STARS_API_URL` GraphQL path until a documented replacement is available.

## Validation

The migration includes unit tests for REST GET/POST/PUT, invalid client IDs, retired update/delete behavior, REST token validation and MCP transport configuration. Live mutation tests are opt-in and use stable client IDs so repeated runs do not create an unbounded number of test records.
