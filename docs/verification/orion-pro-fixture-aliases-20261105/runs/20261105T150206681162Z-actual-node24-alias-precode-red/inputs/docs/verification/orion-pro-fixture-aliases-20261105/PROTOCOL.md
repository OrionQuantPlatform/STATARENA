# Typed fixture aliases — pre-code contract

Suggested commit: `feat: serve versioned typed fixture aliases`.

Two existing route forms: `/api/pitchapi/date/{YYYY-MM-DD}` and
`/api/pitchapi/leagues/{l_ID}/matches`. Current legacy AWS pitch() delegates them
to fixturePage(...,{legacy:true}), which returns `{data:{matches}}` using the
established native-shaped fixture DTO. Its legacy path omits both LIMIT and
pagination. This capability preserves data.matches and its exact DTO, adds an
explicit published pro1 v and bounded keyset pagination, and remains Pro-only.
No new public endpoint, formula, model107 or source/provider fallback is added.

## Scope and version

v is mandatory and names one admitted edition, as in `/api/fixtures?v=pro1...`.
Date+v therefore describes that edition's known fixtures on the calendar day; it
does not claim every competition's matches on earth. A global day consumer must
traverse the relevant manifest edition tokens and all pages. League+v must match
that edition; season is optional and, when present, must equal the edition season.
The current minimal frontend integration is ROOT-owned. No old ProOFF behavior
changes. These aliases must not silently make a first page look like a full list.

Date params: v,status,limit,cursor. League params: v,season,status,limit,cursor.
Status remains all/played/upcoming, defaultall, mapping to finished/not_started as
the existing reader does. Limit1–100/default50. Validate duplicate/unknown params,
invalid dates, oversized values, tokens, enum and limit before facts. Wrong
league/season for a valid v is400. Unknown/malformed route identifiers are400/404.

The response envelope is `{data:{matches:[unchangedFixtureDTO]},pagination}`.
pagination is additive: limit,nextCursor,generation=v. Date NULLS LAST/publicmatchID
C-order applies to league pages; a date route excludes unknown dates. Scores0,
unknown scores/null dates/time/round/playoff/media and all existing key names are
preserved, with no value inferred from absence. The fixture adapter does not
expand frozen summary-v1-shots-v1's DTO or pretend its null image projection is
an exhaustive native source/profile/media response.

The new focused helper may invoke the frozen orionProRoute interface, supplying
the equivalent typed fixture filters. Any alias-level admission/cache/cursor
metadata remains separate. A cursor binds alias path/date/league, season filter,
status, limit and v, including the underlying reader cursor; it cannot be reused
between aliases or the core reader. Historical v remains stable after later
publication, with new v producing corrected rows. GET/HEAD/IfNoneMatch share the
alias's own validator. HEAD/304 are metadata-only/zero body; no fixture list,
appearance/native/heavy family SQL is allowed. SQL count stays constant per page,
without a query per fixture/team. Public data.matches must equal the core reader
for the identical admitted fixture scope, independently checked against the
synthetic fixture's IDs/scores/status/names and source-shaped property set.

## Before-code E2E matrix

Use the already qualified source-free213row EntityFixture with four published
editions/two competitions, same-day ties, unknown date/upcoming, primary/legacy/
manual profiles and wrong-source/noncanonical decoys. No new opaque body or real
source capture; SQL012/013/014/103 remain unchanged. Actual Node24 AWS handler
and read-only runtime; no custom direct-helper-only HTTP adapter.

| Case | Workflow | Expected |
|---|---|---|
| F01 | Native schema/roles, fixture, manifest tokenA |213typed rows; current code pins retained |
| F02 | First valid date alias with vA/limit1 |200 after implementation; actual501 is intended pre-code RED |
| F03 | Date traversal/default/known empty day |Exactlym1,m2 scoped toA; default50; complete empty scope returns no cursor |
| F04 | League traversal limit1 |Exactlym1,m2,m3; no duplicate/loss; null date last |
| F05 | Status scope |Playedm1,m2; upcomingm3; date/upcoming empty |
| F06 | DTO/envelope |Exact existing native-shaped fixture fields and known source values; data.matches equals core reader |
| F07 | Validators first/next/date/league |HEAD200 and matching304, same tag,0bytes/no list or heavy query |
| F08 | Invalid params/date/token/limit |400/no-store, no list/fallback |
| F09 | Cursor cross-scope/limit/status/v/route |400; identical replay stable |
| F10 | Wrong edition league/season |400, no fabricated empty list |
| F11 | Later typed correction/publication |New token yields score/name correction; old token body/tag exact |
| F12 | Unknown-date/nullable fields |m3 retains null date/time/scores and false/unknown remain distinct |
| F13 | Original four readers |Actual manifest/fixture/summary/shots stay served;481bytes unchanged |
| F14 | GET/HEAD/method admission |Two alias forms served, POST405 with Allow; new contract header explicit |
| F15 | Query/row bounds |Constant SQL calls per page;≤100requested rows, no unbounded season list |
| F16 | Boundary/cleanup |0legacy/current sports/source/external calls, source pins exact, all owned resources cleaned |

Proposed one compact coordinated campaign≤90seconds/4000externalSQL/200actualHTTP,
≤5,000typed rows/32MiB evidence/1GiB owned disk/5connections. Do not launch until
ROOT allocates the local PG slot. Stop first failure; preserve exact setup/inputs,
command/pins/expected/actual/HTTP/SQL/logs/cleanup. Original profile/appearance
bundles and their expectations remain immutable; no application wiring until
ROOT is notified and concurrent publisher qualification releases its hold.

UX: bounded, complete traversable lists under a declared edition. DX: existing
typed fixture reader/DTO plus one discoverable wrapper contract. AX: explicit
version/scope, nonportable cursors and metadata validators. Tradeoff: legacy
consumers must adopt v and drain pages before using a list as a full denominator.
