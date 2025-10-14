# GitHub Stars Contributions MCP Server

Model Context Protocol (MCP) server for the GitHub Stars program: <https://stars.github.com/>.

It mirrors the structure of `github-stars-mcp-server` but targets the Stars GraphQL API to create contributions using your personal API token.

- Transport: FastMCP (SSE streamable-http)
- Features: Create contributions in batch

## Configuration

Environment variables:

- STARS_API_TOKEN: Token shown in GitHub Stars profile (Contributions → Token)
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
- MCP_HOST: Bind host for SSE transport (default: 127.0.0.1)
- MCP_PORT: Bind port (default: 8766)
- MCP_PATH: Path (default: /mcp)

## Tools

- create_contributions: Create one or more contributions in a single mutation.

## Quick start

1. Create a virtualenv and install

```bash
cd /home/svg153/REPOSITORIOS/0_PERSONAL/github-stars-contrib-mcp-server
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
```

1. Configure environment (from template)

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

1. Run the MCP server (Streamable HTTP)

```bash
python -m github_stars_contrib_mcp.server
# Binds to MCP_HOST (default 127.0.0.1) and MCP_PORT (default 8766), path /mcp
```

Shortcut with Makefile (loads .env, activates venv if present):

```bash
make run-env
```

Tool contract is defined in `tools/create_contributions.py` (source of truth).
