# Discovery source capability matrix

Discovery is intentionally provider-neutral: adapters return source items/evidence and the deterministic application layer decides normalization, deduplication, confidence, review state and publication eligibility. No source adapter can publish directly to GitHub Stars.

## Capability matrix

| Source | Default capability | Credentials / trust | What is discovered | Explicit limitations |
| --- | --- | --- | --- | --- |
| RSS / Atom | Available | No provider credential; source must be registered | Article/blog entries with stable feed identity and timestamps | Feed content is untrusted; malformed entries may be skipped/reviewed |
| Trusted personal website | Available for explicit/verified ownership | Explicit/verified source; safe fetch | Same-origin feed links plus bounded structured article metadata | No arbitrary recursive crawl; cross-origin feeds are not silently trusted |
| GitHub | Available with token; limited anonymously | Optional `GITHUB_DISCOVERY_TOKEN`, separate from Stars token | Explainable account-owned public contributions that pass eligibility rules | Routine activity is not automatically a Stars contribution; rate limits are surfaced |
| YouTube | Available with API key; limited fallback | Optional `YOUTUBE_API_KEY`; verified channel identity | Channel videos with canonical channel/video evidence | Without key, fallback is public Atom feed only and requires canonical channel ID; no HTML scraping |
| Sessionize / Pretalx-style public speaker sources | Available when public provider data is reachable | Exact verified speaker identity/source | Talks/workshops normalized as Stars `SPEAKING`, with format retained in metadata | No fuzzy identity promotion; provider availability/schema errors are surfaced |
| Explicit event page (`EVENT_PAGE`) | Available for explicitly trusted page | Explicit/verified source URL | One bounded event-page extraction with reviewable evidence | Not auto-classified from arbitrary websites; no site-wide crawl |
| X / LinkedIn exact post URL | Restricted / user-supplied | Exact user-authorized contribution URL | A neutral item from the supplied URL/metadata path | Profiles are not contributions; core server does not scrape post pages or reuse browser sessions/cookies |
| X / LinkedIn local export | Restricted / available when supplied | User-provided neutral export file/data | Items parsed from the export into the common contract | Export is treated as input data, not ownership proof by itself |
| X / LinkedIn compliant API adapter | Optional | Caller supplies a supported/compliant adapter and credentials | Provider-neutral items | No bundled bypass, undocumented API emulation or anti-bot evasion |
| Generic web search | Lead generation only | N/A | Possible source leads outside authoritative write path | A search hit never becomes ownership evidence or direct publication authority |

Capability statuses are explicit (`available`, `limited`, `unavailable`) and provider errors are isolated per source so one broken provider cannot corrupt other source runs.

## Source trust model

Ownership and contribution confidence are separate. A source may be `explicit`, `verified`, `inferred` or `rejected`; disabling a source is also preserved. Inferred ownership never silently becomes verified. Profile links can bootstrap explicit sources, while repeated personal-domain history may produce inferred website sources for human review. Provider-wide domains such as GitHub, YouTube, X or LinkedIn are not inferred as owned merely because an old contribution points there.

## Incremental state

Per-source cursors are stored in the local discovery SQLite database. Adapters use stable provider IDs/canonical URLs so repeated syncs are idempotent. Candidate state and human review decisions are preserved across rediscovery.

Configure the database with `DISCOVERY_DB_PATH`. Without an override the platform-local path ends in `github-stars-contrib-mcp-server/discovery.db` under `%LOCALAPPDATA%` (Windows), `~/Library/Application Support` (macOS), or `$XDG_DATA_HOME` / `~/.local/share` (Linux).

## Publication boundary

Discovery never implies publication. Candidates are compared against Stars before review, exact duplicates are blocked, ambiguous matches remain reviewable, and publication performs another fresh Stars duplicate/policy check. `publish_approved_candidates` defaults to `dry_run=true`; a real write requires a persisted approval plus explicit current invocation with `dry_run=false`.

See [restricted-social.md](restricted-social.md) for the detailed X/LinkedIn contract and [`../security/discovery-threat-model.md`](../security/discovery-threat-model.md) for the threat model.
