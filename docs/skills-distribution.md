# Agent Skills distribution

The four Stars Agent Skills have **one authoring source**: this repository's
`skills/<name>/` directories. The same canonical files are delivered in two different
ways for different client capabilities.

Parent initiative: #48
Standalone-distribution issue: #52
Agent Plugin MCP packaging follow-up: #60

## Decision

Do not create a `stars-skills` repository and do not maintain a second editable copy in
`svg153/skills`.

The supported distribution model is:

| Client capability | Delivery path | Canonical bytes |
| --- | --- | --- |
| MCP client with `io.modelcontextprotocol/skills` | Connect to the Stars MCP server; discover with `skills/list` / `skills/get` and read lazily with MCP Resources | repository/package `skills/*` through the immutable-in-use `SkillCatalog` |
| Client with portable Agent Plugins support but no MCP Skills support | Install/use this repository as the `github-stars-contributions` Agent Plugin | the same repository-root `skills/*` tree |
| APM-based standalone consumer | Depend on the required `skills/<name>` GitHub package locator pinned to an immutable Stars commit | the selected subtree from that exact Stars commit |
| Client with neither mechanism | Use the client's normal Agent Skills import mechanism against a pinned checkout of this repository | the same pinned `skills/*` tree |

`plugin.json` is package metadata only. Agent Plugins v1 discovers skills from the fixed
repository-root `skills/` directory, so the plugin does not require generated copies of
`SKILL.md` in `.agents/`, `.claude/`, `.github/`, or other host-specific directories.

## Agent Plugin MCP server packaging

Agent Plugins 1.0 also defines portable MCP server registration via root `mcp.json`.
Compatible hosts such as VS Code can load plugin-provided Skills and plugin-provided MCP
servers as separate portable component types.

That does **not** make `mcp.json` equivalent to MCP Skills:

- root `skills/*` is package/install-time Agent Skill discovery;
- root `mcp.json` registers an MCP server process/endpoint with the host;
- `io.modelcontextprotocol/skills` is runtime discovery/delivery of Skills from a
  connected MCP server.

The repository intentionally does not ship root `mcp.json` yet. The Stars server requires
`STARS_API_TOKEN` for authenticated Stars operations, while Agent Plugins 1.0 permits a
client to omit or sanitize ambient subprocess environment variables and forbids treating
visible `env`/header package data as a secret mechanism. Depending on an inherited
`STARS_API_TOKEN` would therefore be a host-specific accident rather than a portable
credential contract.

The launcher/auth decision and exit gate are documented in
[`agent-plugin-mcp-packaging.md`](agent-plugin-mcp-packaging.md). Until that gate is met,
the current Agent Plugin remains intentionally Skills-only while the MCP server remains
available through its normal explicit configuration/distribution paths.

## Why the central `svg153/skills` catalog is not mirrored yet

`svg153/skills` already has a strong `MIRRORED_UPSTREAM` mechanism based on APM,
immutable commit resolution, Renovate review, materialization, provenance metadata and
mirror-parity checks. That mechanism is appropriate when central-catalog republication
adds meaningful discovery/install reach.

For Stars today, mirroring all four skills there would add a second **derived payload**
and an extra release/update pipeline without being necessary for standalone use: the
Stars repository itself is already an installable portable Agent Plugin and is the
natural ownership boundary for these tightly coupled workflows.

Therefore #52 deliberately chooses the smaller architecture. If central republication
becomes useful later, it MUST reuse `svg153/skills`' existing APM/Renovate mirror path:

1. add each required Stars skill as an APM dependency pinned to an exact Stars commit;
2. lock that immutable resolution and content integrity;
3. add catalog-owned `metadata.yaml` with `authoritative: upstream`;
4. materialize from the lock rather than copying files by hand;
5. require mirror parity and the normal behavioral/routing gates before merge;
6. update only through reviewed Renovate/APM dependency changes.

Do not introduce a Stars-specific synchronization script to bypass that governance.

## APM consumption without catalog mirroring

An APM consumer can point directly at an individual canonical skill subtree. Use an
immutable commit rather than `main` for reproducibility, for example:

```yaml
dependencies:
  apm:
    - svg153/github-stars-contrib-mcp-server/skills/discover-my-contributions#<reviewed-40-char-commit>
    - svg153/github-stars-contrib-mcp-server/skills/sync-source#<reviewed-40-char-commit>
    - svg153/github-stars-contrib-mcp-server/skills/review-candidates#<reviewed-40-char-commit>
    - svg153/github-stars-contrib-mcp-server/skills/publish-approved#<reviewed-40-char-commit>
```

That is a consumer lock/pin, not a new authority. Changes still originate only in this
repository's `skills/*` tree.

## When both standalone and MCP-served copies are visible

A host can potentially see the same logical skill from a local/plugin installation and
from an MCP server. Do **not** concatenate or silently merge the two instruction bodies.

Recommended origin policy:

1. identify the logical skill by canonical frontmatter `name`;
2. retain origin information (`standalone/plugin` versus `MCP-served/runtime`);
3. if both origins expose byte-identical content/integrity metadata, treat them as two
   delivery paths for one logical skill and activate only one;
4. if their content differs, surface an origin/version conflict instead of pretending
   they are equivalent;
5. when the user is actively connected to the Stars MCP and wants the server-managed
   workflow, prefer the MCP-served copy; when reproducible/offline behavior is required,
   prefer the explicitly pinned standalone copy;
6. never let either copy widen Stars tool authorization. Skill delivery remains separate
   from authentication, review and publish policy.

Not every current host implements origin-aware deduplication. Until hosts converge on a
standard collision policy, users should avoid enabling both copies of the same Stars
skill in one agent session.

## Independence of the MCP runtime

The MCP server does not query APM, the central skills catalog, Renovate, GitHub releases,
or any remote package registry when it starts or serves a skill. Its runtime catalog is
built from the packaged/repository canonical tree.

This is intentional: catalog/discovery infrastructure can fail without taking down MCP
Skills delivery, and standalone installation can exist without changing the server's
authorization or networking surface.

## Update flow

```text
edit canonical skills/* in this repository
  -> review + existing skill contracts
  -> MCP manifest/hash tests + official SEP-2640 conformance
  -> merge
  -> next Stars release / immutable commit becomes a standalone pin candidate
  -> optional external consumers update their pin through their own reviewed dependency flow
```

No reverse synchronization into Stars is allowed. A downstream standalone copy or future
catalog mirror is derived state and must never become the source of truth.
