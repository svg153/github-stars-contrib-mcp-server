# GitHub Stars Contributions MCP Server

Model Context Protocol server for the GitHub Stars program.

## Current compatibility

- **MCP:** official Python SDK 2.x (`mcp>=2.1.1,<3`), implementing protocol revision `2026-07-28` with the SDK's compatibility path for older clients.
- **Contributions API:** `https://stars.github.com/api/contributions` (REST).
- **Profile/links/public Stars reads:** GraphQL remains in use only for surfaces for which the reviewed migration does not document a REST replacement.

GitHub retired the old GraphQL **contribution mutations** on September 1, 2026. The REST API supports authenticated listing, POST creation and idempotent PUT by caller-controlled client ID. It exposes **no contribution DELETE**, so this server does not advertise a delete-contribution MCP tool.

## Configuration

- `STARS_API_TOKEN` — GitHub Stars token.
- `STARS_API_URL` — GraphQL base URL for remaining profile/link/public-profile operations; default `https://api-stars.github.com/`.
- `STARS_CONTRIBUTIONS_API_URL` — Contributions REST URL; default `https://stars.github.com/api/contributions`.
- `LOG_LEVEL` — `DEBUG|INFO|WARNING|ERROR|CRITICAL`; default `INFO`.
- `MCP_TRANSPORT` — `stdio|http|streamable-http|sse`; default `stdio`. `http` is an alias for `streamable-http`.
- `MCP_HOST` — HTTP bind host; default `127.0.0.1`.
- `MCP_PORT` — HTTP bind port; default `8766`.
- `MCP_PATH` — HTTP endpoint path; default `/mcp`.
- `VALIDATE_URLS` — optional lightweight URL validation before writes.

## Contribution tools

- `list_contributions(page=1)` — authenticated REST GET with pagination metadata.
- `create_contribution(data)` — REST POST for one contribution.
- `create_contributions(data)` — REST POST batch (`{"data": [...]}`).
- `upsert_contribution(client_id, data)` — idempotent REST `PUT /{clientId}` with a **complete** contribution payload.

### Breaking update semantics

The old GraphQL `update_contribution(server_id, partial_data)` contract no longer exists. The REST PUT key is a **client ID chosen by the caller**, not the legacy server-generated contribution ID. Reusing an old server ID as if it were a REST client ID can create an unintended new record, so the old update API is rejected rather than silently translated.

Choose stable IDs such as `talk:commit-conf-2026` or `post:my-article-slug` when you want repeatable idempotent writes.

Contribution deletion must be performed in the GitHub Stars web UI because the current REST API has no DELETE method.

## Running

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp env.template .env
export STARS_API_TOKEN='...'
python -m github_stars_contrib_mcp.server
```

For Streamable HTTP:

```bash
MCP_TRANSPORT=streamable-http MCP_PORT=8766 \
  python -m github_stars_contrib_mcp.server
```

SSE remains available only for legacy clients. New HTTP deployments should use Streamable HTTP.

## Local utility

```bash
python scripts/demo.py list-contributions --page 1
python scripts/demo.py create-contributions --data '[{"title":"Example","url":"https://example.com","type":"BLOGPOST","date":"2026-09-01T00:00:00Z"}]'
python scripts/demo.py upsert-contribution \
  --client-id 'post:example' \
  --data '{"title":"Example","url":"https://example.com","type":"BLOGPOST","date":"2026-09-01T00:00:00Z"}'
```

## Testing

```bash
pytest -q
```

Live mutation tests are opt-in with `STARS_E2E_MUTATE=1`. They use stable PUT client IDs rather than POST+DELETE cleanup because the REST API has no DELETE operation.

The source of truth for MCP tool schemas is `src/github_stars_contrib_mcp/tools/`.
