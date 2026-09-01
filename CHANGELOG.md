# Changelog

## 0.2.0 — 2026-09-01

### Breaking

- Migrated GitHub Stars contribution operations from the retired GraphQL contribution mutations to `https://stars.github.com/api/contributions`.
- Replaced partial `update_contribution(server_id, partial_data)` behavior with `upsert_contribution(client_id, data)`, matching REST `PUT /{clientId}` and requiring the complete contribution.
- Explicitly reject the old update API instead of treating a legacy server ID as a REST client ID, which could create a duplicate record.
- Removed the contribution deletion tool because the current REST API exposes no DELETE operation; deletion is performed in the GitHub Stars web UI.
- Replaced third-party `fastmcp` with the official MCP Python SDK 2.x and `MCPServer`.

### Added

- `list_contributions(page=1)` over the authenticated Stars REST endpoint.
- `STARS_CONTRIBUTIONS_API_URL` configuration so contribution REST traffic is isolated from remaining GraphQL profile/link calls.
- REST-based token validation at server startup.
- Stable-client-ID mutation E2E tests that do not depend on unavailable DELETE cleanup.

### Changed

- Raised the MCP SDK floor to `mcp>=2.1.1,<3` (latest mainline stable reviewed for this migration).
- Updated runtime and development dependency floors with next-major upper bounds.
- Updated pre-commit hooks to the current Ruff hook IDs and current hook releases.
- Streamable HTTP is the preferred deployed transport; SSE remains for legacy clients.
- `MCP_TRANSPORT=http` is retained as an alias for `streamable-http`.
- Contribution enum serialization now sends values such as `BLOGPOST`, not Python enum representations such as `ContributionType.BLOGPOST`.

### Compatibility note

The Stars GraphQL endpoint remains only for profile/link/public-profile operations for which the reviewed Contributions migration does not establish a REST replacement. This release intentionally avoids assuming unrelated GraphQL surfaces were removed.
