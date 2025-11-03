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

## Tools

The server provides the following MCP tools:

- **create_contributions**: Create one or more contributions in a single mutation
- **create_link**: Create a link in GitHub Stars profile
- **delete_contributions**: Delete one or more contributions
- **delete_link**: Delete a link from GitHub Stars profile
- **get_stars**: Get the public profile stars/contributions for a GitHub user
- **get_user_data**: Get the currently logged user's data (profile, nominee, contributions)
- **update_contributions**: Update one or more contributions
- **update_link**: Update a link in GitHub Stars profile
- **update_profile**: Update the user's profile information

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
