# GitHub Stars Contributions MCP Server

Model Context Protocol server for the GitHub Stars program.

## Current compatibility

- **MCP:** official Python SDK 2.x (`mcp>=2.1.1,<3`), protocol revision `2026-07-28` with SDK compatibility for older clients.
- **Contributions API:** `https://stars.github.com/api/contributions` (REST).
- **Profile/links/public Stars reads:** GraphQL remains only where the reviewed migration does not document a REST replacement.

GitHub retired the old GraphQL **contribution mutations** on September 1, 2026. Contributions now use REST GET/POST/PUT. The REST API exposes **no contribution DELETE**.

## Supported operations

| Surface | Operation | Transport/API | Important input |
| --- | --- | --- | --- |
| Contributions | List | REST GET | `page >= 1` |
| Contributions | Create one/batch | REST POST | title, URL, type, date; missing description becomes `""` |
| Contributions | Idempotent upsert | REST PUT `/{clientId}` | stable caller-controlled client ID + complete payload |
| Contributions | Delete | Not available | use the GitHub Stars web UI |
| Links | Create/update/delete | Remaining GraphQL | valid `PlatformType`; aliases normalized |
| Profile/public Stars | Read/update where exposed | Remaining GraphQL | existing Stars schema |

Valid link platforms are `TWITTER`, `MEDIUM`, `LINKEDIN`, `README`, `STACK_OVERFLOW`, `DEV_TO`, `MASTODON`, and `OTHER`. Legacy aliases are accepted consistently: `GITHUB -> README`, `WEBSITE -> OTHER`.

## Configuration

- `STARS_API_TOKEN` — GitHub Stars token.
- `STARS_API_URL` — GraphQL base URL for remaining profile/link/public-profile operations; default `https://api-stars.github.com/`.
- `STARS_CONTRIBUTIONS_API_URL` — Contributions REST URL; default `https://stars.github.com/api/contributions`.
- `STARS_AUTH_MODE` — `both|bearer|cookie`; default `both`. REST normally needs bearer auth; `both` also preserves compatibility with remaining GraphQL calls.
- `STARS_USER_AGENT` — diagnostic User-Agent; default `github-stars-contrib-mcp-server/0.3.1`.
- `LOG_LEVEL` — `DEBUG|INFO|WARNING|ERROR|CRITICAL`; default `INFO`.
- `MCP_TRANSPORT` — `stdio|http|streamable-http|sse`; default `stdio`. `http` aliases `streamable-http`.
- `MCP_HOST`, `MCP_PORT`, `MCP_PATH` — HTTP bind configuration.
- `VALIDATE_URLS` — optional lightweight URL validation before writes.

The HTTP client retries transient `429` and `5xx` responses up to three attempts with exponential jitter. Permanent `4xx` errors are returned immediately. GraphQL enum errors for link platforms include the valid `PlatformType` values.

## Contribution tools

- `list_contributions(page=1)`
- `create_contribution(data)`
- `create_contributions(data)`
- `upsert_contribution(client_id, data)`

The old GraphQL `update_contribution(server_id, partial_data)` contract is intentionally rejected: a legacy server-generated ID is not the same thing as the REST caller-controlled `clientId` and translating it can create duplicates.

Choose stable IDs such as `talk:commit-conf-2026` or `post:my-article-slug` for repeatable idempotent writes.

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

## Testing

Unit tests run on every PR/push:

```bash
pytest -q tests/unit
```

Stars API integration tests are isolated in a separate workflow and use `STARS_API_TOKEN` when configured. Mutation tests remain opt-in with `STARS_E2E_MUTATE=1`; they use stable PUT client IDs because REST does not provide DELETE cleanup.

The source of truth for MCP tool schemas is `src/github_stars_contrib_mcp/tools/`.
