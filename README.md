# GitHub Stars Contributions MCP Server

Model Context Protocol (MCP) server for the GitHub Stars program: <https://stars.github.com/>.

It provides a comprehensive API to manage contributions, links, and profile data using your personal API token via the Stars GraphQL API.

- Transport: FastMCP (SSE streamable-http)
- Features: Full CRUD operations for contributions and links, profile management

## Configuration

Environment variables:

- STARS_API_TOKEN: Token shown in GitHub Stars profile (Contributions → Token)
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
- MCP_HOST: Bind host for SSE transport (default: 127.0.0.1)
- MCP_PORT: Bind port (default: 8766)
- MCP_PATH: Path (default: /mcp)
- MCP_TRANSPORT: Transport selection ("stdio" | "http" | "streamable-http" | "sse"). Default: stdio.
- VALIDATE_URLS: Enable lightweight URL HEAD validation before mutations (default: false)
- URL_VALIDATION_TIMEOUT_S: Timeout for URL validation requests (default: 3)
- URL_VALIDATION_TTL_S: TTL cache in seconds for URL validation results (default: 3600)

## Tools

The server provides the following MCP tools:

**Mutations (write operations):**
- **create_contribution**: Create a single contribution
- **create_contributions**: Create one or more contributions in a single mutation
- **update_contributions**: Update one or more contributions
- **delete_contributions**: Delete one or more contributions
- **create_link**: Create a link in GitHub Stars profile
- **update_link**: Update a link in GitHub Stars profile
- **delete_link**: Delete a link from GitHub Stars profile
- **update_profile**: Update the user's profile information

**Queries (read operations):**
- **get_user**: Get the logged user (minimal user info without nominee data)
- **get_stars**: Get the public profile stars/contributions for a GitHub user
- **search_contributions**: Filter contributions from a user's public Stars profile
- **get_contributions_stats**: Get contribution statistics and analytics (groupable by type, month, year)
- **compare_contributions**: Compare contributions between two users
- **export_contributions**: Export contributions in JSON, CSV, or Markdown format

All tools return a standardized response format: `{ "success": boolean, "data": object | null, "error": string | null }`

## Quick start

1. Create a virtualenv and install

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e .[dev]
    ```

2. Configure environment (from template)

    ```bash
    cp env.template .env
    # edit .env and set STARS_API_TOKEN
    set -a; source .env; set +a
    ```

    Alternatively, export variables directly:

    ```bash
    export STARS_API_TOKEN="<your_token>"
    export LOG_LEVEL=INFO
    ```

3. Run the MCP server (Streamable HTTP)

    ```bash
    python -m github_stars_contrib_mcp.server
    # Binds to MCP_HOST (default 127.0.0.1) and MCP_PORT (default 8766), path /mcp
    ```

## Local usage without an MCP client

You can test the tools locally via a tiny demo script. First, make sure a Stars API token is available (export it or put it in a `.env` file at the project root as `STARS_API_TOKEN=...`).

```bash
export STARS_API_TOKEN=stars_...your_token...
```

Then run:

```bash
python scripts/demo.py get-user-data
python scripts/demo.py create-contributions --data '[{"title": "Test Contribution", "url": "https://example.com", "type": "BLOGPOST", "date": "2023-01-01T00:00:00Z"}]'
```

Shortcut with Makefile (loads .env, activates venv if present):

```bash
make run-env
```

Tool contracts are defined in `src/github_stars_contrib_mcp/tools/` (source of truth).

### Enums and aliases

For link platforms, see `PlatformType` in `src/github_stars_contrib_mcp/models.py`. The tools also accept a couple of legacy aliases which are normalized internally by `normalize_platform` in `src/github_stars_contrib_mcp/utils/normalization.py` (e.g., `GITHUB` → `README`, `WEBSITE` → `OTHER`). When an alias is used, a warning is logged to help migrate callers.

## Testing

Unit tests:

```bash
. .venv/bin/activate
pytest -q
```

All tests, with optional live mutation e2e:

```bash
# Create `.env.local` with at least STARS_API_TOKEN; set STARS_E2E_MUTATE=1 to enable mutation tests
make test-all
```

Notes:

- If your token doesn’t expose nominee data, read/profile flows may be skipped by tests (that’s expected).
- Ensure `LOG_LEVEL` is one of: DEBUG, INFO, WARNING, ERROR, CRITICAL.

## Features and Roadmap

This project includes comprehensive improvements planned across 10 key areas:

- Security and Authentication
- Error Handling System
- Data Validation
- Performance Optimizations
- Complete Documentation
- CI/CD Automation
- Monitoring and Observability
- Advanced Testing
- Advanced Features
- Advanced Architecture

See `docs/feats/README.md` for detailed implementation plans and phased rollout strategy.
