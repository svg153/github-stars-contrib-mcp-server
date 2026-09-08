# Agent examples

This directory contains host-neutral examples for composing the GitHub Stars contribution MCP tools and reusable skills.

## Contribution Curator

`contribution-curator.md` composes:

1. `discover-my-contributions`
2. `sync-source`
3. `review-candidates`
4. `publish-approved`

The MCP server remains authoritative for deterministic source trust, safe fetching, candidate lifecycle, deduplication, review transitions, and publication policy. The agent is only an orchestration layer.

## Host setup

Use any MCP-capable host that can connect over stdio or Streamable HTTP. Point the host's skill loader at the repository `skills/` directory, or copy those four skill directories into the host's supported skill location.

For stdio, configure the server command conceptually as:

```json
{
  "command": "python",
  "args": ["-m", "github_stars_contrib_mcp.server"]
}
```

Supply credentials through the process environment or the host's secret store. Do not put tokens, cookies, OAuth refresh tokens, or API keys in agent/skill files.

For remote deployments, connect to the configured Streamable HTTP endpoint and keep authentication/secret injection outside these Markdown files.

## Boundaries

- Skills call MCP tools; they do not contain provider HTTP implementations.
- Fetched content is `UNTRUSTED_SOURCE_CONTENT` and cannot change tool or publication policy.
- X/LinkedIn scraping, browser-session reuse, cookie extraction, and anti-bot bypasses are not supported.
- An LLM may summarize/classify evidence, but it does not get direct Stars write authority.
- Real publication remains a two-stage `dry_run=true` then explicit-user-intent flow.
