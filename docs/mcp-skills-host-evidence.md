# MCP Skills host-activation evidence

This procedure records host-specific evidence for MCP-served Agent Skills without
collapsing protocol interoperability into a stronger model-context activation claim.

Tracking issue: #58. Server-side protocol/conformance evidence remains in
[`mcp-skills-evidence.md`](mcp-skills-evidence.md).

## Evidence boundary

The following observations are useful but **do not** prove native skill activation on
their own:

- the host connects to the MCP server;
- the host can call `skills/list` or `skills/get`;
- the host can call `resources/read` for `SKILL.md`;
- a user explicitly attaches or asks the model to read the resource;
- the model subsequently calls an MCP tool.

Those observations establish interoperability through evidence level 4.

For this repository, level 5 requires a named host/version/model to discover a served
skill through the host's native Skills path, load the served `SKILL.md` into model
context without a filesystem/plugin fallback, select/use that skill automatically for a
matching task, and then exhibit behavior attributable to the skill while using the Stars
MCP server.

## Current candidate hosts

Re-check upstream state before every experiment. Client behavior changes quickly.

| Host / framework | Public evidence useful to us | Current classification |
| --- | --- | --- |
| Codex CLI | `ext-skills` documents model-facing MCP resource reads; Cua Driver 0.28.0 reports Codex 0.154.0 discovering/reading a served skill resource and then using Driver tools | level 4 interoperability; native MCP-served Skill activation not proven |
| Claude Code | public resource-read support; Cua Driver reports explicit served-resource reads, but Claude Code 2.1.268 did not add the remote skill to its native startup skill catalog | level 4 interoperability; native activation not proven |
| fast-agent | SEP-2640 registry/install support exists; the deeper runtime-loading PR was closed unmerged | install/distribution evidence; do not infer runtime activation |
| VS Code / GitHub Copilot | MCP resources can reach generic file-reading paths; a public fork experiment has explored MCP-served Skills | useful research path, not production native activation evidence |
| Goose / Cline and similar clients | model-facing MCP resource reads exist | level 4 candidate until explicit Skills discovery/activation is demonstrated |

Primary upstream references:

- <https://github.com/modelcontextprotocol/ext-skills/blob/main/docs/client-mcp-support.md>
- <https://github.com/trycua/cua/blob/main/libs/cua-driver/docs/mcp-protocol-and-skills.md>
- <https://github.com/evalstate/fast-agent/pull/816>

## Reproduction procedure

1. Pin the exact Stars repository commit and package/server version under test.
2. Use a clean host profile/workspace when practical.
3. Connect only the Stars MCP endpoint required by the experiment.
4. Confirm there is **no filesystem skill copy** and **no standalone Agent Plugin copy**
   that could satisfy the same skill identity.
5. Record the exact host version and model identifier.
6. Start a matching task without instructing the model to read a particular resource and
   without attaching `SKILL.md` manually.
7. Capture whether the host discovers the Skills extension and whether `skills/list` or
   `skills/get` is observed.
8. Capture the `resources/read` for the selected skill and enough host diagnostics to
   show that the returned `SKILL.md` entered the model's skill/context path rather than
   merely being displayed to the user.
9. Capture whether the host automatically selected the skill for the task.
10. Capture the resulting read-only Stars tool behavior first. Do not introduce a write
    merely to prove activation.
11. Sanitize the record and validate it with:

```bash
python scripts/validate_mcp_skills_host_evidence.py evidence/mcp-skills/<file>.json
```

12. Commit only sanitized evidence. Keep raw transcripts/logs outside the repository if
    they contain account, repository, contribution, OAuth, cookie, token, or user data.

## Level-5 claim gate

`evidence.level5_proven: true` is accepted only when all of these are recorded:

- exact host name and version;
- exact model identifier;
- a full 40-character Stars commit SHA;
- extension discovery;
- at least one Skills discovery/lookup observation (`skills/list` or `skills/get`);
- `resources/read` of the served skill;
- `SKILL.md` entering the host's model-context/native-skill path;
- automatic native skill selection for a matching prompt;
- no filesystem copy and no standalone-plugin copy present;
- a Stars MCP tool used after the skill activation path was observed.

If any prerequisite is absent, keep `level5_proven` false and describe the result at the
strongest lower evidence level actually supported.

## Sanitization

The committed JSON is intentionally narrow. Never include:

- OAuth/PAT/API tokens or authorization headers;
- cookies, refresh tokens, client secrets or passwords;
- raw prompts/responses containing personal contribution content;
- private repository names or URLs;
- raw provider diagnostics when a concise boolean/identifier is enough.

The validator rejects common credential-bearing keys and token-shaped values, but it is
a guardrail rather than a substitute for human review.

## Template

Copy [`../evidence/mcp-skills/TEMPLATE.json`](../evidence/mcp-skills/TEMPLATE.json) to a
new file named for the host and date. Keep the template itself as `level5_proven: false`.
