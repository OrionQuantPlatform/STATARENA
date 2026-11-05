# Appearance adapter review

Suggested commit: `feat: serve versioned typed season appearances`.

Status: implementation written after the retained actual-app A02 RED, followed
by actual Node24 HTTP22/22 and existing-consumer acceptance. Exact measured
results and their limits are in BILAN.md and the immutable run result. This
document explains the source; it is not independent runtime evidence.

The new module owns only `/api/seasons/partition`. It requires an exact published
single-edition pro1 token and matching league/season. Its adapter version is
`normalized-season-v1-native31`; original summary/shots V1 and entity DTOs remain
unchanged. Match pages are ordered by date NULLS LAST/public match ID using C
collation, and cursors bind token, adapter, edition, limit and packed format.

Admission checks every selected full-match performance in the edition, not only
the page. The accepted producer and period must match; selected participant,
source record, source/variant and native field bindings must be complete. There
must be exactly31 canonical registered standard native states per accepted row,
consistent numeric projections, finite numeric grammar and safe integer bounds.
Explicit normalized_performance coverage supplies the denominator and present/
empty distinction. Missing coverage/native states return a named503/no-store.

Typed foreign-key anchors establish ownership of retained historical parents.
Selected match sides therefore join by logical match ID at dg, rather than
requiring their match_revision_id to equal a later selected match revision.
Coverage likewise retains its valid match anchor. Performance/native participant
anchors still match exactly, with selected canonical participant rows at dg.

The participant's physical observed profile supplies name/playerRef. Resource
profile precedence cannot replace it. Raw position/shirt type and presence,
nullable starter/captain, coordinate frame and registered boolean reliability
are preserved. No mutable identity label or missing-flag default is introduced.

The SQL native payload carries `[field,kind,text-or-bool-or-null]` tuples. Only
validated numeric text becomes JSON.rawJSON at serialization; typed text/boolean/
null never becomes a number. The packed table encoder carries those exact tokens
and missing-property indexes. Existing consumers intentionally retain their
existing derived IEEE64 arithmetic, including unweighted appearance ratings.

Metadata includes coverage/cardinality/projection validation and the whole
edition's linked media dependency fingerprints before HEAD/304. The media map is
captured once per request, validates hash/key/MIME/canonical-origin, and uses
explicit revalidation. Historical tokens do not falsely promise immutable media.

Whole-edition team/competition context accompanies each bounded page. Match team
statistics are normalized from typed columns with unknown values omitted/null;
there is no fabricated team clearance/aerial statistic. Shots/events/heatmaps are
not loaded by this projection. The empty transport arrays are explicitly marked
lazy/unknown and do not claim collected-empty source families.

The22 pre-code cases exercise actual Node24 HTTP, independent Decimal wire
parsing, existing packed decoding, full450minute/30peer cohorts, top8 player
similarity and existing club summaries/top6 similarity. Efficient backend
aggregate delivery and every remaining detailed route remain later work; this
adapter is not a full backend or real-data cutover claim. The current real core
still needs qualified normalized_performance coverage and structural source facts
where its importer has not preserved them.

UX: existing consumers receive scoped, observed typed rows. DX: one versioned
module and existing encoder/algorithms. AX: bound cursors, named admission errors,
actual HTTP traces and exact numeric evidence. The tradeoff is explicit503 when
the complete-input contract cannot be established; no first-page or fake-empty
denominator is substituted.
