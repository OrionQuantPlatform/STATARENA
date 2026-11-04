# Saved-data bridge acceptance follow-up — 4 November 2026

Scope: local frontend bridge only. The immutable previous Vercel deployment
is the sole external read source. Do not read a provider API, write remote
data, repeat the RDS pair, deploy, change environment configuration, or change
the UI layout. Parent owns release and independent review.

Before changing fixture handling, run an HTTP E2E with these saved-response
faults: a null fixture, an absent ID, a numeric ID and an empty ID. Each must
return 503/DATA_UNAVAILABLE, without returning a partial successful page.
A valid duplicate identity must remain deduplicated, valid records must retain
their full values, and status/date/league/season filtering and cursor traversal
must remain unchanged. A legacy query at its 20,000-row cap must fail closed.
Preserve the first red receipt, then make only the required validation change
and rerun the same complete HTTP workflows. These are synthetic HTTP E2Es,
not proof of live malformed data or production Neon SDK behaviour.

Real-data follow-up must measure the actual supplemental index and expand
its saved table references through the current client with concurrency at most
four. Bound external reads to 300 unique requests, 64 MiB total response bytes,
30 seconds per request, and existing public saved objects only. Record object
counts, aggregate bytes, decoded row counts, elapsed times, actual maximum
concurrency and semantic equality. Never persist the football row payloads.
The `/api/supplemental` whole-payload response must either match those objects
within the 2 MiB compatibility response cap or explicitly return 413; the UI's
bounded-object client path must work independently of that large response.

Compare the exact browser player `p_3chd12` honours path with the saved source,
including status, content hash and the real client's 404 result. A matching
source 404 is missing saved honours data, not a bridge regression. It must not
be converted to a fabricated 200 response.

Inventory every current UI route family and filters from the checked-in call
sites. Execute representative current/historical league and calendar fixture
filters, multi-season historical enumeration, six-season scoped loading,
player/team scouting histories, match subresources, archives (results/goals),
rankings, native and imported cup snapshots/tables, supplemental catalogs,
stored projection routes, assets and existing error/cache semantics. Record
source-backed 404s and uncovered cases as limitations. Synthetic fault checks
must be separately labelled. A local Next build and local-shim browser cannot
qualify a real credentialed Vercel preview or production runtime limits.

Every E2E saves setup, exact rerun command, expected/actual outcomes, input
paths, source hashes and logs or content hashes. Preserve failed artifacts.

Suggested commit: `fix: fail closed on malformed saved fixture pages`.

## Archive payload failure found by the expanded browser

The 2020/21 archive browser workflow is red: its goals endpoint returns 413.
The saved source is present (238,411 gzip bytes, 2,677,442 JSON bytes). Before
changing the product, run a focused real HTTP workflow through the existing
catalog client; it must receive the exact decoded saved JSON, original ETag
and cache metadata, HEAD without a body and conditional GET 304. Invalid or
duplicate kind/season stays 400, an absent season stays 404, and source failure
must stay visible. A synthetic saved-object metadata size above 2 MiB must
still fail with 413 without exposing a partial body.

Chosen fix: serve an archive season's existing saved gzip representation with
JSON content type and `Content-Encoding: gzip`; cap its encoded size at 2 MiB.
Use the existing legacy reader for file metadata, validators, HEAD and bytes.
Do not lift the generic JSON cap, alter client APIs/UI, recompress data, write
objects or change the explicit AWS branch. This preserves the URL/JSON contract
and avoids parsing/reserializing the large archive in the compatibility layer.
Actual Vercel handling of encoded headers remains a credentialed-preview gate.
Save the focused first red, green HTTP receipt and the affected browser rerun.

The first post-fix browser relay deleted every source `Content-Length`, causing
the new metadata guard to return 503. This is a harness mismatch: the actual
legacy file handler and focused real HTTP source retain encoded lengths. Fix
the relay to remove lengths only when fetch decoded an HTTP content coding;
retain correct raw `.gz` lengths and preserve that failed browser receipt.
The relay also buffers a response in memory before forwarding: Bun sends a
streamed GET as chunked and drops its supplied length, even though HEAD keeps
it. This second local HTTP hop does not exist between the actual compatibility
handler and legacy reader. Preserve its 503 receipt too; do not relax the
product metadata guard to hide a test relay mismatch.

Suggested commit: `fix: serve saved archive gzip without expanding response size`.
