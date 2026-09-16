# Agent Plugin MCP packaging decision

Tracking issue: #60
Related distribution docs: [`skills-distribution.md`](skills-distribution.md)

## Status

**Decision: do not ship a root `mcp.json` yet.**

The repository already conforms to Agent Plugins 1.0 for portable Skills through
`plugin.json` + the canonical `skills/*` tree. Agent Plugins 1.0 also defines portable
MCP server registration through root `mcp.json`, and VS Code/Copilot consumes that
component type. The missing piece is not the launcher itself; it is a portable,
credential-safe way for the stdio process to obtain `STARS_API_TOKEN`.

Adding an `mcp.json` that only works when a client happens to inherit the editor/shell
process environment would overstate portability and would contradict the published
Agent Plugins 1.0 subprocess-environment rules.

## Sources of truth checked

As of 2026-09-16:

- published Agent Plugins specification: <https://agent-plugins.org/specification>
- portable MCP configuration: <https://agent-plugins.org/plugin-authors/mcp-servers>
- canonical 1.0 schemas:
  - <https://agent-plugins.org/schemas/1.0.0/plugin.schema.json>
  - <https://agent-plugins.org/schemas/1.0.0/mcp.schema.json>
- VS Code Agent Plugins implementation/docs:
  <https://code.visualstudio.com/docs/agent-customization/agent-plugins>

The public website still marks **1.0.0** as the published specification. Development
work for later versions in the specification repository is not a reason to target an
unpublished schema here.

## What the standard gives us

Agent Plugins 1.0 has two portable component types:

1. Agent Skills discovered under root `skills/`;
2. MCP servers discovered from root `mcp.json`.

For stdio MCP servers, the portable config can provide:

- a single `command` token;
- `args`;
- `env` values;
- `cwd`;
- `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` expansion in `args`, `env` values and `cwd`.

Clients must provide `PLUGIN_ROOT` and `PLUGIN_DATA` to plugin subprocesses. The client
chooses the base subprocess environment and may inherit, omit or sanitize ambient
variables. The specification explicitly says a conforming plugin must not depend on a
base-environment variable unless the specification requires it or the server config
supplies it explicitly.

That rule is decisive for Stars authentication.

## Why inherited `STARS_API_TOKEN` is not a portable solution

The Stars server currently requires `STARS_API_TOKEN` for real Stars API access. The
obvious local config would be approximately:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "github-stars-contributions": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--project",
        "${PLUGIN_ROOT}",
        "github-stars-contrib-mcp-server"
      ],
      "cwd": "${PLUGIN_ROOT}"
    }
  }
}
```

This launcher shape is structurally portable, but it does not solve credentials. It
would only authenticate when a particular client decides to preserve an ambient
`STARS_API_TOKEN`. Agent Plugins 1.0 allows the client to omit or sanitize that variable,
so the plugin cannot claim portable authenticated operation on that basis.

Putting the token into `mcp.json.env` is forbidden for this project because config values
are visible package data and the standard explicitly says they are not a portable secret
mechanism. The same applies to literal HTTP headers.

## Launcher decision

When credentials are solved, **local stdio remains the preferred first packaging path**.
The repository already exposes the console script:

```text
github-stars-contrib-mcp-server
```

A `uv` launcher is a reasonable candidate because it can execute the project directly
from the installed plugin checkout. To avoid writing a virtual environment into a plugin
package, a future config should evaluate a client-data environment such as:

```json
"env": {
  "UV_PROJECT_ENVIRONMENT": "${PLUGIN_DATA}/venv"
}
```

and run with `${PLUGIN_ROOT}` as the project/cwd. This is only a launcher design note; it
must be validated on Windows, macOS and Linux and against an actual source-installed
Agent Plugin before shipping.

A published `uvx`/package launcher may become simpler after #72 establishes a stable
public package. That can improve installation UX but still does not solve credential
bootstrap by itself.

## Credential bootstrap options

A future implementation must choose a credential source that does not require portable
plugin metadata to contain the secret and does not depend on ambient-environment
inheritance.

### Option 1: server-owned secure credential store

Add an explicit setup command that stores the Stars token in the operating-system secret
store/keyring under a stable service/account identity, then let the MCP server resolve it
when `STARS_API_TOKEN` is absent.

Requirements before choosing this route:

- setup/status/delete lifecycle;
- no token on stdout/logs;
- useful behavior on Windows/macOS/Linux;
- defined behavior when no secure keyring backend exists;
- environment variable remains an explicit override for current deployments/tests;
- no model/agent prompt is used to collect the secret.

This is the strongest candidate for a local stdio plugin if cross-platform UX proves
acceptable.

### Option 2: remote Streamable HTTP + client-managed authorization

Agent Plugins 1.0 intentionally leaves remote authorization client-managed. A stable
remote Stars MCP endpoint with a standards-compatible authorization flow could therefore
be packaged without literal auth headers.

Do not choose this route until there is a real deployed endpoint and an reviewed auth
model. The current repository does not provide that production service boundary.

### Option 3: client-specific secret configuration

VS Code/Copilot or another client may offer a native secret/input mechanism outside the
portable Agent Plugins core. That can be documented as an optional client adapter, but it
must not be represented as portable Agent Plugins behavior and should not become the only
supported path if this repository claims portable `mcp.json` packaging.

## Rejected approaches

Do not ship any of these:

- a literal `STARS_API_TOKEN` in `mcp.json`;
- `${STARS_API_TOKEN}` or other invented environment interpolation in `mcp.json`;
- an `Authorization`/cookie/API-key value in portable HTTP headers;
- `DANGEROUSLY_OMIT_AUTH=true` as the normal plugin runtime merely to make startup green;
- a launcher that silently assumes VS Code, Copilot CLI or another client inherits shell
  environment variables;
- a host-specific duplicate of the four canonical Skills just to work around MCP startup.

## Failure semantics

The absence of `mcp.json` does **not** invalidate the current Agent Plugin. Skills remain
portable and installable from the existing canonical tree.

When a future `mcp.json` is added, Agent Plugins failure isolation remains important: an
MCP server that cannot start/connect/authenticate must not prevent the plugin's Skills
from loading.

## Validation added now

The repository has two guard layers for the current and future package:

1. unit tests keep canonical Skill identities single-source and reject credential-like
   material if a future root `mcp.json` appears;
2. the `Agent Plugin Schema` workflow validates `plugin.json` against the canonical
   published Agent Plugins schema and automatically validates `mcp.json` against the
   matching canonical schema once that file exists.

Schema validation is deliberately separate from the semantic auth decision: a JSON file
can be schema-valid and still be an unsafe or misleading credential design.

## Exit gate before adding root `mcp.json`

All of the following must be true:

- [ ] one portable credential/bootstrap strategy is implemented and documented;
- [ ] the strategy does not depend on ambient-environment inheritance;
- [ ] no secret appears in plugin package metadata;
- [ ] launcher works from a source-installed plugin checkout;
- [ ] writable dependency/runtime state uses client-managed writable storage rather than
      modifying the installed plugin package where practical;
- [ ] Windows, macOS and Linux behavior is understood;
- [ ] root `mcp.json` passes the canonical 1.0 schema;
- [ ] real VS Code/Copilot smoke test shows Skills still load and the MCP server can make a
      read-only authenticated Stars call;
- [ ] existing SEP-2640 server conformance stays unchanged/green.

Until that gate is met, keeping `mcp.json` absent is the safer and more accurate product
state.
