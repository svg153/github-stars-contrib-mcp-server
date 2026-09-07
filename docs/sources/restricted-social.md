# Restricted social sources: X and LinkedIn

The v0.3 discovery pipeline treats X and LinkedIn as **restricted providers**. It is intentionally useful without browser automation and intentionally refuses to turn authentication or product limitations into a scraping problem.

## Supported modes

| Mode | v0.3 core | Network access | Credentials |
| --- | --- | --- | --- |
| `explicit_url` | Supported | None | None |
| `export_import` | Supported | None; local file only | None |
| `official_api` | Extension point | Provider API only | Provider-specific OAuth/token |
| Browser/session scraping | Unsupported | Not permitted | Not permitted |

There is no `scrape` capability and no fallback from an unavailable API to browser automation, authenticated session cookies, residential proxies, or undocumented endpoints.

## Explicit post URLs

Register the exact X status or LinkedIn post/update URL as an explicit or verified source. The adapter stores that URL as evidence and may use user-supplied metadata such as `title`, `text`, `published_at`, `author`, or `contribution_type`.

The v0.3 core does **not** fetch X/LinkedIn HTML implicitly. Missing date/type information remains missing and therefore review-required; it is not guessed.

Example source metadata:

```json
{
  "social_mode": "explicit_url",
  "title": "Launching my open-source project",
  "published_at": "2026-09-07T10:00:00Z",
  "contribution_type": "OTHER"
}
```

## Local export/import

Set `social_mode` to `export_import` and `import_path` to a local UTF-8 `.json` or `.csv` file. Files are read by the local MCP process and are never uploaded by this adapter.

Neutral JSON schema version 1:

```json
{
  "schema_version": 1,
  "provider": "x",
  "posts": [
    {
      "id": "123",
      "url": "https://x.com/example/status/123",
      "title": "Optional title",
      "text": "Optional post text",
      "published_at": "2026-09-07T10:00:00Z",
      "author": "optional-handle",
      "contribution_type": "OTHER"
    }
  ]
}
```

CSV uses the columns `schema_version,provider,id,url,title,text,published_at,author,contribution_type`. `provider` accepts `x`/`twitter` or `linkedin` and must match the registered source.

Native provider export layouts are not guessed. A provider-specific mapper should only be added when a current documented format and fixtures are available.

## Official API adapters

A compliant OAuth/API connector implements the existing `SourceAdapter` contract. Provider credentials must be injected through constructor/DI and must never be stored in `SourceRecord`, candidate evidence, logs, prompts, or Stars credentials. `SourceCapability.permissions` declares required scopes and authentication failures remain explicit instead of switching transport.

The core currently reports `official_api` as unavailable until such a connector is installed/configured. This keeps the boundary honest while allowing future first- or third-party integrations.

## Security and review

Imported or user-supplied social text remains untrusted evidence. It cannot trigger tools or publication. Explicit URL and export modes never use authenticated sessions, and publication still requires the deterministic review/publish policy used by all other sources.
