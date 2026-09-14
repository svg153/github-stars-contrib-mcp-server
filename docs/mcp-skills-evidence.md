# MCP-served Agent Skills: conformance and evidence

This document records what the Stars MCP implementation has actually proven about
`io.modelcontextprotocol/skills`, and deliberately separates protocol evidence from
agent/host activation claims.

Parent initiative: #48
Conformance/security issue: #51
Host-activation follow-up: #58

## Reuse-first baseline

The implementation and its evidence reuse upstream MCP work instead of maintaining a
parallel protocol stack:

- the server uses the official MCP Python SDK 2.x `Extension`, `MethodBinding`,
  `ResourceBinding`, `FunctionResource`, and `MCPError` primitives;
- the CI gate uses the official
  [`modelcontextprotocol/conformance`](https://github.com/modelcontextprotocol/conformance)
  SEP-2640 server scenarios, pinned to an immutable commit;
- the official
  [`modelcontextprotocol/inspector`](https://github.com/modelcontextprotocol/inspector)
  already contains first-class Skills schemas and Skills client support and remains a
  useful interactive inspection path;
- the upstream
  [`modelcontextprotocol/ext-skills`](https://github.com/modelcontextprotocol/ext-skills)
  research is used to track real host/client adoption rather than inferring support from
  generic MCP resource support.

## Evidence levels

| Level | Claim | Current evidence | Status |
| --- | --- | --- | --- |
| 1 | Structural/unit conformance | Catalog, manifest, path, symlink, malformed-frontmatter, duplicate-identity, integrity-drift and permission-boundary tests | **Proven** |
| 2 | MCP protocol round-trip | Real official Python SDK `Client` tests for `skills/list`, `skills/get`, pagination, errors and `resources/read` | **Proven** |
| 3 | Extension discovery | `server/discover` plus official `sep-2640-skills-enumeration` conformance scenario | **Proven when CI is green** |
| 4 | Lazy resource loading and integrity | Exact SHA-256/size verification in tests plus official enumeration/manifest conformance scenarios | **Proven when CI is green** |
| 5 | An agent host automatically discovers, activates and uses a served skill in model context | No Stars-specific host activation run is recorded yet | **Not proven** |

A green level 1-4 result MUST NOT be described as level 5.

## Official conformance gate

`.github/workflows/mcp-skills-conformance.yml` starts the real Stars server over
stateless Streamable HTTP with no Stars API token and runs the official MCP conformance
suite at commit:

`7169291ec0b68eb370fddcd9947313ab0d5e4156`

The workflow executes these SEP-2640 scenarios independently:

- `sep-2640-skills-enumeration`
- `sep-2640-skills-manifest`
- `sep-2640-skills-directory`

`directoryRead` is intentionally not advertised. The directory scenario therefore
checks the optional-capability boundary rather than creating a second recursive read
surface unnecessarily.

Each job uploads its conformance result directory and the local server log for 30 days.
The evidence run contains no Stars token: `DANGEROUSLY_OMIT_AUTH=true` disables Stars
mutation tools for this isolated protocol test server.

## Security and integrity boundaries

### Static manifest authority

Every skill is discovered from the canonical repository/package skill tree. The catalog
records every served file, exact byte size and SHA-256 digest. `resources/read` can read
only a URI already present in that immutable-in-use manifest.

If canonical bytes change after a catalog has been constructed, the existing catalog
fails closed instead of serving bytes under stale integrity metadata. Reconstructing the
catalog produces a new digest and size.

### Path and origin safety

The catalog rejects symlinked roots, symlinked skill directories, symlinked files,
filesystem escape, malformed manifests and unknown resource URIs. Percent-encoded
traversal strings are not decoded into filesystem paths; because they are not exact
manifest-authorized URIs they fail as unknown resources.

Skill identity is tied to the parent directory: frontmatter `name` MUST equal the
canonical directory name. A second directory cannot claim an existing identity and be
accepted as an alias.

### Skill text is not authorization

Skills are instructions and metadata, not an authorization mechanism.

The Skills extension contributes only:

- `skills/list`;
- `skills/get`;
- standard MCP Resources for manifest-authorized skill files.

It contributes no tools and does not intercept `tools/call`. In particular,
`allowed-tools` is preserved as Agent Skills frontmatter metadata but is never interpreted
by the Stars server as permission to register, expose, authorize or invoke a Stars
mutation tool.

The existing Stars authentication/review/publish rules therefore remain outside the
Skills delivery path.

## Compatibility landscape

Upstream `ext-skills` research documents model-facing MCP resource access in clients such
as Codex, Goose, Claude Code, Cline and VS Code/GitHub Copilot. It also documents
fast-agent as a shipped SEP-2640 registry/install implementation. Generic
`resources/read` support and registry/install support are useful, but neither is
sufficient evidence that a host natively discovers and activates a served Agent Skill in
model context.

A recent independent implementation gives a useful negative boundary. Cua Driver 0.28.0
reports that Codex 0.154.0 and Claude Code 2.1.268 can discover/read its MCP-served skill
resources and then use server tools. The same report explicitly does **not** classify
those runs as native skill activation; Claude Code did not add the remote skill to its
native startup skill catalog. That distinction matches this repository's evidence model.

The Stars repository therefore keeps level 5 open rather than manufacturing a stronger
claim from client resource access. Candidate-host evidence and the exact reproduction /
sanitation contract are tracked in
[`mcp-skills-host-evidence.md`](mcp-skills-host-evidence.md) and #58.

## Host-specific level-5 gate

A future level-5 record must identify the exact host, host version, model and Stars
server commit. It must also show that:

- the host discovered the Skills extension and a served skill;
- the served `SKILL.md` entered the host's native skill/model-context path;
- the skill was selected automatically for a matching task;
- no filesystem skill copy or standalone Agent Plugin copy supplied the same behavior;
- a Stars MCP tool was used after the activation path was observed.

Committed evidence must pass:

```bash
python scripts/validate_mcp_skills_host_evidence.py evidence/mcp-skills/<file>.json
```

The validator also rejects common credential-bearing fields and token-shaped values. Raw
host transcripts remain out of the repository when they contain user/account/provider
content.

## Exit criteria for #51

#51 can close when:

- normal repository CI is green;
- all targeted official SEP-2640 conformance jobs are green (or the optional directory
  scenario is explicitly skipped because `directoryRead` is undeclared);
- security/integrity negative tests remain green;
- no mutation or publish permission has been introduced by Skills metadata;
- this document reflects the actual evidence and does not claim level 5.

Once those conditions hold, this implementation is suitable as the reference pilot for
`svg153/skills#64` and the no-duplicate distribution work in #52. Level 5 is deliberately
tracked as the independent #58 follow-up rather than retroactively weakening #51's
completed server-side evidence criteria.
