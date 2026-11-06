# Six typed match-detail readers — protocol before implementation

Suggested commit: `feat: serve six versioned typed match detail routes`.

Owner: backend_entities. ROOT owns the router, approved schema/migration,
publication and shared contracts. No PostgreSQL campaign may start until ROOT
has read this protocol and allocated its bounds. No source, provider, Neon, RDS,
S3 or credential access is part of this work.

The six existing forms are the core match, momentum, events, lineups, h2h and
stats endpoints under `/api/pitchapi/matches/{match}`. The new production module
will be `dashboard/backend/services/orion-pro-match-details.js`. It remains
separate from reader 481, entity 950, appearance b3d4, fixture aliases and all
existing evidence bundles. Those contracts are preserved exactly. Stats/advanced
player families outside these six forms remain another category.

## Approved inputs and representation binding

The user approved the targeted 107-table extension in
`../orion-pro-match-details-20261104/USER_APPROVAL_20261105.json`. The separate
approved model is `docs/architecture/orion-native-details-107-20261105/target-schema.approved-107.json`,
SHA256 `f516804f6e2381b5e55763860b6470127b88a567006973afa79c0a9f5f0d9ae3`.
Its 98 active tables have 1,823 columns and 447 foreign keys. Original model 103,
the compiler and sealed 012/013/014/015 remain unchanged. ROOT is implementing
append-only migration 016; its availability/qualification is a dependency, not
an excuse to substitute an opaque body or mutate the old schema.

The authoritative shared interface is
`../orion-pro-native107-20261105/PUBLICATION_BINDING.json`:

* Build representation remains `summary-v1-shots-v1`, with the original pro1
  grammar and original four-reader DTOs.
* The distinct publisher uses `orion_pro_publish_native107_v1` and metrics
  contract `orion_pro_native107_v1`. Its existing dependencies_sha256 binds the
  independently computed V1 and native closures, model 107 and effective dg/cg.
  The native closure must include core observation details and momentum as well
  as the four amended families; a momentum-only change must invalidate its token.
* Native requests explicitly select `representation=match-native-v1` and retain
  `v=<exact pro1>`. A separate `nv=<native1>` pins the native representation.
  The native token uses the exact 12-string array in PUBLICATION_BINDING.json,
  including source pro1, build ID, dg/cg, joint digest, model, contract, code and
  environment. No second build representation or mixed-current group is added.
* First-request discovery can use HEAD with representation+v, returning native1;
  subsequent reads pin nv. If ROOT requires nv on discovery too, a concrete token
  discovery interface must be supplied before the reader fixture is frozen.
  No unrelated endpoint is invented implicitly.
* Responses identify `X-Orion-Native-Version: match-native-v1`,
  `X-Orion-Native-Representation: native1...` and the source pro1 separately.
  ETags bind route, query, source/native tokens and any separately delivered media.
  Historical tokens and explicit revalidation must remain honest.

Invalid query syntax, duplicate/unknown fields, malformed tokens or mismatched
v/nv/build/snapshot/contract return 400 without payload reads. Missing native
admission, a legacy READY103 build, unrecorded or inconsistent data returns a
named 503/no-store. Unknown match membership returns 404. An absent source family
is never inferred from missing SQL rows. Methods are GET/HEAD; other methods are
405. ROOT will integrate dispatch after the actual reader RED and source review.

## Fidelity boundary for the six routes

| Route suffix | Target and exact source boundary |
|---|---|
| events | Exact amended native fields, actor/sub-in objects, parent source order and root native match ID |
| lineups | Exact amended home/away objects, coach-name-only object, standard label, arrays/order, member types and raw coordinates |
| stats | Exact period/group/item layout, including empty containers, repeated keys, titles/formats and physical native scalar refs |
| h2h | Exact observed summary totals and ordered recent list, including unresolved IDs, false finished and empty recent list |
| core match | `CORE_MOMENTUM_FIELD_MATRIX.json` maps all 20 observed leaves. Three real gaps remain in approved 107: referee, has_playoff and immutable league.image_url. An exact native request remains explicitly unavailable until the proposed six-column extension is approved and qualified. The original normalized summary stays available. |
| momentum | All three observed leaves are representable for the qualified numeric `provider_native` series, with exact count and sample order. Existing double columns do not prove absent/null states or arbitrary native precision. Unqualified shapes or multiple/foreign series are refused, never flattened or rounded by guess. |

The four amended families and qualified momentum retain `data` in their admitted
native shape. Metadata outside `data` identifies contract, tokens, collection
state and fidelity. The core route reports its explicit missing native fields
under approved 107; it does not return a deceptively complete partial `data`.
The additive 017 fields have separate user approval and a distinct model/binding.
CORE_017_E2E.md governs their owned verification. The 016 workflow still tests
f516 and its precise core refusal; no full six-route parity is claimed by it.

Native source image URLs remain immutable observed facts in `data`. Typed asset
references and canonical CDN delivery are separate. A media correction must not
rewrite the source URL fact; any ancillary delivery map has its own mutable
dependency and revalidation. No backend fetch of a source URL is allowed.

## Exact cohorts and source states

Coverage is selected at dg by its complete physical parent key:
`(match_id, source_id, feature_code, variant_key, recorded_from_gen)`. The root
record is exactly `/data` in one immutable document. Root native match ID is its
external_key under source_match_id_state. Public route aliases remain separate.
Aliases/catalogue dependencies use cg; no current view, latest row, name guess
or cross-edition publication lookup resolves a captured native field.

The agreed counters are events = event objects, h2h = recent_matches, stats =
top-level periods, lineups = the two declared home/away headers. Lineup member
and stats period/group/item counts are separate at their declared nesting level.
An explicit array absent/null uses SQL NULL count, empty uses zero, present uses
its exact positive count. A source-declared absent/null collection is distinct
from unavailable/unrecorded knowledge; the latter cannot acquire a fake body.

Exact locators are `/data/events/<i>`, `/data/recent_matches/<i>`,
`/data/periods/<i>/groups/<j>/items/<k>`, `/data/home` and `/data/away`, then
`/starters/<i>` or `/subs/<i>`. Ordinals are nonnegative canonical decimal text,
without leading zeros except 0. Source/document/parent equality, uniqueness and
contiguous counts establish the complete cohort. Ordering uses the explicit
source ordinal, never minutes, labels, timestamps or physical row IDs.

Native profiles use exact actor ownership, source/document/actor-object locator,
context `native_match_observation_v1:<record>`, variant `source:exact` and the
approved pinned-cg eligibility. Wrong global, other-source and same-name decoys
cannot substitute. These new native rules are distinct from the legal retained
legacy profile case already qualified by 8 additional tests: closing an old
legacy profile must not break those original readers or appearance b3d4.

Canonical selection chooses the family observation. Explicit physical native
member/scalar refs may be noncanonical aggregate observations. A lineup parent
change can require member replacement; a layout-only stats change may retain
unchanged physical scalar rows. Repeated actor occurrences and stat keys are
preserved rather than deduplicated. H2H totals are never derived from list length;
finished is never derived from scores/status. Related player is not sub-in player.

Fixed scalar states preserve absent/null/value. Objects preserve absent/null/
object; arrays preserve absent/null/empty/present. Unrecorded is never inferred
to any of these. Empty string, false and numeric zero remain values. Unknown
identity/type/field extensions block admission explicitly, without retention loss.

Sporting numeric values use finite PostgreSQL numeric text and JSON.rawJSON
without Number conversion. Both 9007199254740993 and 0.8200000000000000001 must
remain numeric JSON lexemes, verified by independent Python Decimal parsing.
IDs stay validated bigint/ASCII decimal strings, and ordinal/count conversions
use separate checked integer bounds. Native31's unsafe-integer rejection is an
unchanged earlier contract, not a bound silently applied to these native facts.
NaN/Infinity tokens never serialize as numbers; text containing those words
remains text. Existing integer source domains must reject out-of-domain values.

## Before-code E2E matrix

Use one owned PostgreSQL 18.6 with exact 012–016, the approved model and ordinary
writer/runtime roles. A separate synthetic HTTP fixture covers A/B plus an
independent C, all six routes, explicit source records, periods/mappings and
native observations. No real source body is read or staged. For the first reader
RED/AFTER, ROOT authorized a separately labelled synthetic READY creator under
the ordinary writer role and active guards, with independent SQL digests of the
actual typed fixture graph and the exact joint binding. Arbitrary READY flags or
digest strings are forbidden. This qualifies reader behavior on a real typed
graph; the actual production publisher and its no-op/atomicity proof remain a
separate required workflow. No fixture result substitutes for it.

The HTTP server invokes actual aws-app.handleRequest under Node 24. The portable
runtime check records actual version/platform/architecture and verifies an
explicit platform-matching official archive/SHASUMS input; it must not depend on
a Darwin-only archive path on Linux. Existing consumer decoding/field access and
independent Decimal/own-property/object/array order oracles inspect real bodies.

| Case | Workflow | Required observable outcome |
|---|---|---|
| R01 | Schema, roles and old four-reader baseline | Exact old source/DTO/ETag, native role deadlines and read-only access |
| R02 | Valid published native fixture before app dispatch | Actual baseline app returns 501, later cases unverified; once wired, same request must return exact native events |
| R03 | Native request binding and discovery | Exact 12-string native token, source v, representation and headers; no mixed pair |
| R04 | Core native admission under approved 107 | Named 503 with the three known unrecorded fields; original normalized summary remains exact. Native core success requires the separately approved and qualified 017 workflow. |
| R05 | Momentum ordered points | Source sample order and exact qualified numeric minutes/negative/zero values. Unknown minute or foreign/multiple series refuses native admission instead of inventing state. |
| R06 | Events basic source states/order | Empty type, period, minute 0, added 0, score 0, false booleans and absent/null preserved |
| R07 | Events duplicate display values | Equal minute/player/type objects remain separate and source-ordered |
| R08 | Distinct player and sub-in objects | Correct exact profiles, IDs/name/image/position states; no related-player substitution |
| R09 | Native profile decoys | Wrong global/source/locator/context rejected; no preferred-resource fallback |
| R10 | Native root teams and IDs | Captured root objects and raw native IDs differ safely from public aliases |
| R11 | Lineup header shape | home/away object/null/absent, standard, formation, confirmed and coach-name-only exact |
| R12 | Lineup lists and order | Starters/subs empty/null/absent/present and repeated actor slots preserved |
| R13 | Lineup native scalar states | Shirt 0/'09'/null/absent, captain false, position string/number and exact raw coordinates |
| R14 | Native scalar/profile agreement | Same-source member/profile position/shirt agreement; contradiction rejected by seal/admission |
| R15 | Stat periods/groups/items | Empty period/group, repeated raw keys, exact titles, empty format and source order |
| R16 | Stat value kinds | Exact numeric/empty string/'07'/false/null/absent, including the two large/long numeric cases |
| R17 | Stat physical membership | Noncanonical referenced scalar selected by its physical ref; wrong side/source/period refused |
| R18 | H2H empty recent list | Observed nonzero totals survive recent=[]; no total/list equality invented |
| R19 | H2H finished and unresolved IDs | False finished with 0–0, blank time/status, labels/images and no invented cross-edition link |
| R20 | Known empty versus absent/null | Explicit source collection states reproduce the shape; missing/unavailable/unrecorded does not become [] |
| R21 | Wrong or partial coverage | Named 503/no-store, no payload/source fallback; native publication cannot certify partial input |
| R22 | Locator/slot/count negatives | Gaps, leading-zero index, duplicate slot, foreign document/parent/source refused, native constraints active |
| R23 | Admitted family HEAD and matching 304 | Five admitted family validators agree, zero body and bounded metadata only; unavailable core retains its named metadata error; no native sporting payload scan |
| R24 | Conditional mismatch | Returns the correct complete GET body and validator, without stale token/body mixing |
| R25 | Invalid params/method/token | 400/405 before payload; nv without native representation or a mixed v/nv rejected |
| R26 | Layout-only correction | New native/joint/pro1 tokens despite unchanged V1 summary; new layout exact, old token stable |
| R27 | Reuse unchanged scalars | New stats layout can retain admitted scalar revisions without dedup or source mismatch |
| R28 | Native correction and independent C | Atomic A/B effects, unchanged C token/body/304, old native source captures preserved |
| R29 | Repeated input/no-op | Ordinary guarded fixture publisher adds no generation/build/publication/sequence on identical typed input; actual production publisher no-op remains separate |
| R30 | Legacy/profile and V1 coexistence | Old closed legacy capture still readable; old four-reader bytes/ETags and ProOFF behavior unchanged |
| R31 | Size/work bounds and numeric failures | Explicit 413/503, no silent truncation/coercion; no N+1 queries or full-edition value revalidation for validators |
| R32 | Permissions, boundary and cleanup | Runtime writes denied; zero legacy/current/source/provider access; exact pins and owned cleanup |

Metadata HEAD/304 must trust only a qualified immutable READY joint contract and
bounded coverage metadata. It does not rehash every native sporting cell on each
request. Publisher certificates are not invented by the reader. If qualification
is missing, return an explicit admission error, not a false metadata success.

Proposed local resource bounds: one owned cluster, at most 5,000 typed rows,
600 seconds, 4,000 external SQL calls, 200 actual HTTP requests, 64 MiB evidence,
1 GiB owned disk and 5 connections. Proposed reader limits are 1,000 events,
2,000 momentum points, 500 H2H entries, 2 lineup headers with at most 80 members,
16 stat periods, 128 groups and 1,000 items, and a 1 MiB encoded body. These are
response limits, not source retention or fixture-denominator caps. Counts use
full declared scopes; any excess produces an error rather than a complete-looking
truncated list. The budget is at most 6 SELECTs for GET, 2 for HEAD/304, no query
per member. Byte-size excess is detected while encoding GET; HEAD is not a
measurement of encoded bytes. The request ledger is frozen before allocation. The 016 workflow runs R01–R32,
including no more than 73 public requests and their individually fetched SQL
traces (146 actual HTTP requests). The separate 017 workflow reruns the baseline
subset stated in CORE_017_E2E.md before its append/cases.

Every run retains setup, input/schema/contract/code hashes, exact command,
expected/actual case results, HTTP bodies, SQL/Node/Decimal logs and cleanup.
Stop the first unexpected failure. Missing 016, publisher qualification or a
valid fixture is reported as setup/unverified, not a passing reader workflow.
No cloud application, deployment or cutover is implied by local acceptance.
