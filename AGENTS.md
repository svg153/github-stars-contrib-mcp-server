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
- MCP_TRANSPORT: Transport selection ("stdio" | "http" | "streamable-http" | "sse"). Default: stdio.

## How to run locally

- Setup virtual environment: `make venv` (creates `.venv` directory)
- Activate virtual environment: `source .venv/bin/activate`
- Install: `pip install -e .[dev]`
- Start server: `python -m github_stars_contrib_mcp.server`

Server binds to 127.0.0.1:8766 by default (SSE transport).

## Testing

- Unit tests: `pytest -q`
- Full suite: `make test-all`
- To enable live mutation e2e tests, set `STARS_E2E_MUTATE=1` and provide a valid `STARS_API_TOKEN` in `.env.local`.

## Safety and limits

- Auth: requires the GitHub Stars API token for mutations
- Errors: HTTP and GraphQL errors are surfaced in the `error` field

## References

- FastMCP: tool registration via `@mcp.tool` decorator
- See `src/github_stars_contrib_mcp/tools/create_contributions.py` and `src/github_stars_contrib_mcp/tools/get_user_data.py` for canonical tool definitions

Notes for contributors (minimal):

- Settings live in `src/github_stars_contrib_mcp/config/settings.py`. Avoid relying on any legacy config modules; use the canonical settings.
- Platform values for links are validated against `PlatformType` (see `src/github_stars_contrib_mcp/models.py`). The tool layer performs minimal normalization via `utils/normalization.normalize_platform` (e.g., `GITHUB` → `README`, `WEBSITE` → `OTHER`). Prefer sending canonical enum values; aliases are supported for backwards-compat only and log a warning.

## Workspace agents & prompts (VS Code)

Minimal pointers to workspace prompts that accelerate common tasks (see `.vscode/prompts/`). The prompts reference the code as the source of truth—avoid duplication.

- MCP development: `mcp-python-expert.prompt.md` — repo-aware assistant for adding/updating tools safely.
- Tests & coverage: `tests-and-coverage.prompt.md` — run tests, read coverage, propose focused fixes.
- PR authoring: `pr-description.prompt.md` — concise PR template.
- Release notes: `release-notes.prompt.md` — generate notes from git history.
- Stars tools: `stars-contrib-tools.prompt.md` — guidance for using server tools instead of raw API.
- Copilot coding agent hand-off: `github-coding-agent.prompt.md` — template to delegate implementation to GitHub Copilot coding agent.

Note: Prompts are intentionally brief; consult tool definitions under `src/github_stars_contrib_mcp/tools/` for exact schemas.

## New agents, chat modes, and instructions

These live under `.vscode/` and are repo-aware (minimal, code-referential):

- Agents (`.vscode/agents/`):
  - `release-manager.agent.md` — prepare concise release notes and optional version bump
  - `test-maintainer.agent.md` — keep tests/coverage healthy, propose focused fixes
  - `docs-minimizer.agent.md` — enforce minimal docs policy referencing code
  - `get-user.agent.md` — fetch the current GitHub Stars logged user via the `get_user` MCP tool and return minimal JSON

- Chat modes (`.vscode/chatmodes/`):
  - `python-mcp-expert.repo.chatmode.md` — expert MCP dev guidance bound to this repo
  - `tests-tdd-green.repo.chatmode.md` — TDD-Green focused on pytest + Makefile

- Instructions (`.vscode/instructions/`):
  - `docs-minimalism.instructions.md` — workspace docs policy
  - `stars-api-safety.instructions.md` — safety rules for Stars API usage
  - `engineering-standards.instructions.md` — global repo engineering standards
  - `testing-strategy.instructions.md` — unit/integration separation, coverage, mocks
  - `fastmcp-contracts.instructions.md` — tool schemas, response contract, context usage

- Agent (`.vscode/agents/`):
  - `engineering-guardian.agent.md` — guardrail reviewer for PRs/chats
