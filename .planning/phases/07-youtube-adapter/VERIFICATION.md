# Phase 07 Verification — YouTube discovery adapter

**Issue:** #23
**PR:** #31
**Verified head:** `9342ca2921b997d3d88414cc94219aaaf85d0530`
**GitHub Actions:** `tests` run #56 — success

## Requirement evidence

### YT-01 — Trusted channels use supported API/feed mechanisms
**Result:** verified.

- `normalize_youtube_channel` distinguishes channel identities from individual video/playlist URLs.
- `YouTubeSourceAdapter` uses YouTube Data API v3 `channels`, uploads `playlistItems`, and batched `videos` metadata.
- `YouTubeFeedSourceAdapter` uses only the public channel Atom endpoint via `ContentFetcher`; it never fetches or parses YouTube HTML.
- DI selects Data API when `YOUTUBE_API_KEY` is present and the limited Atom adapter otherwise.

### YT-02 — Canonical video/channel evidence
**Result:** verified.

- Data API candidates use stable external IDs `youtube:video:<video_id>` and canonical watch URLs.
- Evidence records channel ID, video ID, discovery mode and publication timestamp when available.
- Feed candidates preserve the canonical channel ID and mark `limited_history=true` so reduced coverage is visible to review/policy layers.
- SQLite contract tests prove both API and feed paths survive the common source → candidate → evidence persistence flow.

### YT-03 — Missing credentials/quota is explicit, never scraping
**Result:** verified.

- Missing `YOUTUBE_API_KEY` does not disable YouTube entirely when a canonical channel ID is known; capability becomes `LIMITED` through the public Atom feed.
- Handles/custom URLs without a canonical channel ID are unavailable in credential-free mode rather than scraped for resolution.
- API quota/rate-limit reasons classify as `RATE_LIMIT`; rejected keys/access classify as `AUTH` and make the adapter unavailable.
- No authenticated browser cookies, HTML scraping or video-page ownership inference exists in the implementation.

## CI evidence

- Pre-commit: passed in run #56.
- Ruff check/format: passed in run #56.
- Offline unit/contract suite: passed in run #56.

## Exit gate

Phase 07 exits successfully: trusted YouTube channels can produce evidence-backed video contribution candidates through supported API/feed mechanisms, with deterministic cursors and explicit limited/error capability behavior and no scraping bypass.
