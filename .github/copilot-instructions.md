# GitHub Stars Contributions MCP Server - AI Coding Instructions

## Architecture Overview
This is a Model Context Protocol (MCP) server built with FastMCP that provides tools for managing GitHub Stars contributions via GraphQL API. It follows clean architecture principles:

- **Domain Layer** (`src/github_stars_contrib_mcp/domain/`): Ports defining contracts (e.g., `StarsAPIPort`)
- **Application Layer** (`src/github_stars_contrib_mcp/application/`): Use cases orchestrating business logic
- **Infrastructure Layer** (`src/github_stars_contrib_mcp/utils/`): Adapters like `StarsClient` implementing ports
- **Presentation Layer** (`src/github_stars_contrib_mcp/tools/`): MCP tools with `@mcp.tool()` decorators

Data flows from tools → use cases → ports → adapters → external Stars API.

## Critical Workflows
- **Setup**: `make venv` (creates `.venv`), `source .venv/bin/activate`, `make install` (installs with dev deps)
- **Run Server**: `python -m github_stars_contrib_mcp.server` (binds to 127.0.0.1:8766 by default)
- **Test All**: `make test-all` (requires `.env.local` with `STARS_API_TOKEN`; enables e2e mutations if `STARS_E2E_MUTATE=1`)
- **Unit Tests**: `pytest -q` (runs with coverage)
- **Lint/Format**: `ruff check --fix .` and `ruff format src`

## Project-Specific Conventions
- **Enums**: Use canonical `PlatformType` values (e.g., `README` not `GITHUB`); legacy aliases auto-normalized with warnings logged
- **Validation**: Optional URL HEAD validation via `VALIDATE_URLS=true` (default false, 3s timeout)
- **Logging**: Structured logging with `structlog`; levels via `LOG_LEVEL` env var
- **Responses**: All tools return `{success: bool, data: object|null, error: string|null}`
- **Dependencies**: Injected via `di/container.py`; prefer ports over direct imports
- **Normalization**: Descriptions trimmed/stripped; platforms mapped (see `utils/normalization.py`)

## Integration Points
- **Stars API**: GraphQL mutations/queries via `utils/stars_client.py` (httpx + tenacity retries)
- **Auth**: Requires `STARS_API_TOKEN` from GitHub Stars profile; validated on startup
- **Transports**: Supports stdio/http/streamable-http; configured via `MCP_TRANSPORT`

## Key Files
- `src/github_stars_contrib_mcp/models.py`: Pydantic models and enums (e.g., `ContributionType`, `PlatformType`)
- `src/github_stars_contrib_mcp/shared.py`: FastMCP app instance and client initialization
- `src/github_stars_contrib_mcp/tools/`: Tool implementations (reference for new tools)
- `src/github_stars_contrib_mcp/utils/queries.py`: GraphQL query/mutation strings
- `.vscode/prompts/`: Repo-aware prompts for specific tasks (e.g., `mcp-python-expert.prompt.md` for tool development)

## Examples
- **Adding a Tool**: Create in `tools/`, use `@mcp.tool()`, validate with Pydantic, call use case, handle errors
- **Platform Handling**: Input `GITHUB` → normalized to `README` with warning log
- **Testing**: Add unit tests in `tests/unit/`, integration in `tests/integration/`; run `make test-all` for full coverage</content>
