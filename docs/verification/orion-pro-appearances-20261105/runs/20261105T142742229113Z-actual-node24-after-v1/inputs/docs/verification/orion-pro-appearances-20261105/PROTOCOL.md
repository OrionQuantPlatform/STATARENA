# Typed normalized appearances and existing player cohorts — pre-code contract

Suggested commit: `feat: serve typed appearances and existing player cohorts`.

Scope: new focused reader module/fixtures/E2E, later minimal actual-app dispatch
coordinated with ROOT. Keep the original V1 reader, entity helper95021ded, both
earlier evidence bundles, model103 and sealed012/013/014 exact. No source/provider/
RDS/cloud calls or normalizer/model edits. No new scoring algorithm.

## Versioned reader boundary

Existing `/api/seasons/partition` requires league, season and one pro1 edition v;
the scope must match that edition. Limit1–100/default25 and a token/filter-bound
match-key cursor select a total order `(date NULLS LAST, public match ID COLLATE C)`.
Both JSON and existing `format=columns` return the established partition envelope
`{data,pagination}` with tables that decodePartition can consume. Metadata names
the new normalized representation and its exact projection; heavy match families
are lazy, never advertised as collected-empty merely because omitted from this
projection. This is not a silent expansion of summary-v1-shots-v1.

ROOT's pre-code scope refinement keeps the existing partition seam first. No new
scouting endpoint is added in this lot: aggregateSeasonPlayers/buildCohorts/
rankMetric/similarPlayers and club analysis are exercised through the real typed
HTTP pages using the unchanged existing consumer algorithms. Dedicated efficient
backend aggregate delivery remains the next coherent product when the frontend
seam requires it; this transport proof is not its completion. The initial additive
target-route proposal is preserved in design/INITIAL_PROPOSAL.md. The57-route
inventory therefore gains one admitted existing form, with41other forms remaining
after the earlier8entity+4native+3operational/media forms. No deferred score table,
weighted-rating substitution or new formula is introduced.

## Admission and exact data rules

* Resolve an actual published build/token before facts. Require canonical selected
  match/participant/stats versions and exact match-team/player/period/source/
  variant bindings at dg; aliases/dimensions use cg. Stable identity labels and
  source-body/legacy/current tables are forbidden as fact/profile fallback.
* The exact physical profile referenced by a selected participant supplies the
  observed performance name/playerRef; a preferred global resource profile must
  not replace it. Unknown name remainsNULL in the public DTO. Position/shirt
  states preserve absent/null/string/number; starter/captain remain nullable.
  Registered boolean quality indicator stats_reliable may supply statsReliable;
  missing/unknown does not become false or true. Source role/raw coordinates and
  the87legacy-column mapping retain their explicitly documented qualification gaps.
* Native31 uses the producer contract real_source_core_v2_native31, family standard,
  metric names legacy_normalized_<field>, exact source record/variant/period and
  participant revision. Every accepted performance needs all31 scalar-state rows,
  including explicit absent/null. A missing SQL row is unknown, not absent.
  Common numeric projection and typed native scalar must agree; nonnumbers require
  NULL numeric projections. No extra source family can be selected accidentally.
* Typed per-match coverage feature normalized_performance must explicitly declare
  present/empty and the exact selected row count/source/variant. A missing/partial/
  unavailable coverage record blocks this complete-input contract503. These states
  describe the captured normalized input projection, not universal sports coverage.
  Real core native31 facts alone do not supply this admission metadata; the data
  owner must produce it from qualified source metadata, never by missing-row inference.
* Facts preserve numbers as JSON number tokens using JSON.rawJSON, strings as
  strings (including empty and07), booleans as booleans, null as null, absence by
  omitted property. Numeric tokens must match finite JSON numeric grammar, and
  internal IDs/counts/BigInt handling have explicit safe bounds. NaN/Infinity and
  unsafe/unbounded integer conversions fail, never becoming null/rounded values.
  Independent Python Decimal parsing verifies wire values under actual Node24;
  Bun alone is insufficient. Packed format must retain the same property states.
* Derived cohort arithmetic intentionally preserves the existing browser's IEEE64
  numeric behavior on genuinely numeric source values. Text/bool/null are never
  coerced to numbers. Raw fact transport remains exact independently of this
  existing derived arithmetic contract. Ratings use known appearance mean, not
  minutes-weighted mean. Full denominator/450minute/30peer rules are preserved.
* Query/numeric display filters must not secretly truncate or select the peer
  distribution. Any full-cohort computation must traverse all admitted selected
  inputs, not a first page or a local qualification cap. Representational page
  bounds do not constrain denominators. Empty/unknown fields remain distinguishable.
* Source performance IDs must resolve unambiguously from immutable source_records;
  no invented ID is used to hide collisions. All referenced public IDs are scoped.
* Metadata/coverage/native cardinality/media dependency validation occurs before
  content. HEAD/matching304 have zero bodies and no native-value payload query.
  Media follows the verified typed SHA/key/MIME/canonical-origin policy and explicit
  revalidation; historical facts are not given a false immutable-media promise.

## Pre-code E2E matrix

The owned fixture extends the immutable first-lot fixture with32players/12teams,
6rounds/36matches/192performances and5952native31 states, plus exact typed parents,
coverage and publications. All inputs are synthetic and saved; no real source
body is read or staged. Total typed-row budget is explicitly8,000 for this lot.
No5000-row cap from earlier qualification lots is silently reused.

| Case | Workflow/input | Expected outcome |
|---|---|---|
| A01 runtime/setup | exact schema/role + representative fixture |94tables/read-only, <8krows, all ready-build guards intact |
| A02 actual routing RED | valid version/edition + absent new module |actual app501 before implementation; all later cases unverified |
| A03 bounded traversal | limit2 across36matches |192unique source appearance IDs, no missing/duplicate match, terminal cursor |
| A04 scalar wire | absent/null/0/string07/empty/false/exact long decimal |independent Decimal/type/own-property equality; no coercion |
| A05 packed roundtrip | same page JSON andcolumns |existing decodePartition produces same observable rows/states |
| A06 cold validators | page HEAD/IfNoneMatch |zero bytes, metadata only, validator agreement |
| A07 validation/scope | unknown/duplicate/invalid/token mismatch |400/404 without content/source fallback |
| A08 cursor scope | cross limit/format/version/edition |400/409; frozen traversal stable |
| A09 missing native field | legal typed generation lacking one scalar |503, never advertised complete/absent |
| A10 coverage absent/partial | no qualifying normalized admission |503/no-store; unknown is not empty |
| A11 source/variant | legal noncanonical/other-family decoys |exact primary canonical selection only |
| A12 corrected publication | changed value/new build + old reread |new value/tag; old facts/ETag unchanged |
| A13 cohort completeness | complete HTTP traversal into existing consumer, default450minutes/30peers |full selected inputs, exact metric count/minutes coverage |
| A14 rating | one45minute10rating + five90minute6ratings |known appearance mean40/6, not weighted mean |
| A15 similarity | source descriptors versus decoded HTTP rows through existing pure algorithms |exact ordered top8 IDs/parts, matching numeric result |
| A16 filter independence | existing consumer display/query context after complete input |peer distribution never reduced to visible/first-page rows |
| A17 threshold edge | changed peerMinutes/partial metric observations |existing eligibility/null-rank rules, no fabricated percentiles |
| A18 actor/profile | physical observed profile versus global decoy |source observed name/ref retained; unknown stays unknown |
| A19 media | linked typed media and same-ID hash correction |revalidation/HEAD/304 correct;0object/provider HTTP |
| A20 numeric safety | finite grammar/integer boundaries/NaN/Infinity |explicit error, no silent null or type conversion |
| A21 Node24 | actual pinned v24.22.2 server/serializer |process.version recorded; exact Decimal wire cases |
| A22 closure/cleanup | full trace/roles/owned lifecycle |0legacy/current sports/source reads;0external; all owned processes/dirs closed |

ROOT allocated the first setup+actual-router RED up to600seconds/4000external SQL
calls/200actual HTTP/96MiB evidence/1GiB owned disk/5connections, with an8ktyped-row
fixture and at most1000native rows per COPY batch. This is a local qualification
allocation, not a production scope cap. Publisher's parallel work is setup-only;
no heavy/unbounded fixture is allowed.

Each real run will save the command, exact setup/inputs/hashes, expected/actual
case outcomes, complete HTTP/SQL/Node/Bun/Decimal logs and cleanup. PG slots are
coordinated with ROOT; one owned cluster, ≤8ktyped rows and ≤200actual HTTP are
proposed, with an explicit bounded wall-clock allocation before launch. Stop at
the first unexpected failure and preserve it. No check is passed until executed.

UX: real typed profile/season data with the existing descriptive calculations.
DX: reuse the pure source algorithms and version the wire adapter. AX: explicit
coverage/admission, bound cursors, exact states, inspectable failures. Tradeoffs:
some current real data needs truthful admission/structural mapping before it can
serve this complete-input product; importing those facts is distinct from coding
the reader and does not justify reducing scope or inventing defaults.
