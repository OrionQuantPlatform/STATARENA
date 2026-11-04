# Version-pinned frontend data client, before implementation

Suggested commit: `feat: pin frontend match pages and lazy details to published representations`.

This lot first adds a data-access client; it does not claim React/browser or Vercel acceptance. Its E2E uses the actual local Pro HTTP server, owned PostgreSQL 18.6 and complete publication fixture from `orion-pro-readers-20261104`. No provider, source document, S3, Neon or remote RDS action is allowed. The production bridge remains unchanged.

Public module contract: `services/pro-match-data.js` exports `loadProManifest(fetcher)`, `ProMatchClient({manifest,leagueId,season,fetcher,cache})`, `createProMatchCache({maxBytes,maxEntries})`. The client exposes `representationToken`, `page(filters)`, `summary(matchId)`, `shots(matchId)` and `resourceKey(kind,id)`. It selects exactly one manifest edition, sends its opaque `v` on every request and never follows archive/provider fallbacks. Summary attaches the verified token to the returned match. Shots preserve native fields and explicit empty/unavailable states.

| Case before code | Expected observable workflow |
|---|---|
| Missing client module | Initial RED; dependent cases unverified, no remote action |
| Unsupported/malformed/ambiguous manifest edition | Reject; no legacy fallback or request |
| Request a page of two matches | One list GET, two rows, no automatic traversal or heavy query; second requested page completes three unique IDs |
| Open a summary concurrently | One HTTP request for the same token/ID; lightweight summary; caller mutation cannot poison cached data |
| Request shots explicitly | No earlier shots request; native zero/null/false/empty preserved where present; empty and `NOT_COLLECTED` differ |
| Publish corrected A/B while C remains independent | New manifest yields new A/B tokens; old clients retain old values; C reuses its token/cache |
| Response token does not match request | Reject and evict failure; never cache under the wrong version |
| Oversized successful response | Return it without evicting a smaller useful cache entry or retaining the oversized object |
| Resource identity | Same match under a new token has a distinct key; identical token/ID reuses its key |

The HTTP fixture is mutated only through the existing typed publisher on the owned local database. The driver and server exchange phase-control signals through subprocess pipes, not production endpoints. Evidence retains setup, exact commands, source hashes, synthetic inputs, HTTP traces, SQL operation counts, outcomes, original failures and owned-process cleanup. The cache is bounded by bytes and entry count; in-flight deduplication is separate from retained entries so an oversized result cannot flush the useful cache first.

The real application's season-wide context and its React resource keys will be integrated in a later explicit browser step. This component's passing result must not be described as that UI integration or as production latency improvement.
