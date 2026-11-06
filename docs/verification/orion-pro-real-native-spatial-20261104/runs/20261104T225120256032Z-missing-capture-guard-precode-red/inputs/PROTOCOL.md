# Pre-capture failure matrix and complete workflow

This protocol and E2E precede the new capture guard and candidate wrapper.
Preparation is source-free. Real execution requires a separately approved
commit whose normalizer bytes equal MANIFEST.normalizerSha256 and an explicit
source-authorized flag. ROOT must review this protocol/test before that flag is
used. The old89-query ledger is checked byte-for-byte and never opened for write.

| Failure or edge | Required observable result |
|---|---|
| Missing query/byte checkpoint, negative/bool/nonzero counters, missing ledger, wrong limits/state | Refuse before any source connector or HTTP client; no ledger reset |
| Another capture owner, replay after claiming, vanished socket | Refuse; no source fallback; prior budget persists |
| Query12, HTTP4, byte33554433 or excess physical bytes | Refuse before send/decode beyond limit; journal attempt/failure metadata |
| Wrong source host/db/TLS/read-only/isolation/timeouts, changed pointer/SHA/selector/status/ordinal | Refuse exact source; no alternate origin/path or broad scan |
| Gzip size/hash/ETag or decoded count mismatch | Bounded read/decode refuses; no body file; capture stays consumed |
| New auth required or existing credentials unavailable | Metadata-only blocked receipt; no login or credential output |
| Native field missing/null/0/empty string/string/bool/fraction/large precision | Source kind/value must equal registered SQL scalar exactly; no missing-row-as-absent and no coercion to0/1 |
| Numeric projection | NUMERIC exact; count exact nonnegative int32; double finite shortest-decimal round-trip; incompatible native number rejects, never rounds/drops |
| Definition/unit or participant/period/source/variant/generation mismatch | Independent SQL oracle fails even if numeric sums match |
| Sparse triplet order/zero/corners/duplicate coordinates/bounds | One row per observed triplet, exact source ordinal/x/y/actions, no absent-cell zero; invalid collection rejects atomically |
| Grid/frame/metres and actions/cells state | Only explicit qualified values; preserve orientation/units, no extra rotation; unavailable states distinct |
| Direct response provenance | Source document explicitly Neon, exact SHA/bucket/key/version; root empty+dataRoot/data; every parent/coverage locator resolves correctly |
| Cross-origin identity/cohort mismatch | Report exact IDs and refuse spatial observation; no invented participant/profile/played or source authority |
| Restart/reimport | Fresh exec uses same RAM; exact receipts/bindings and all table/sequence fingerprints unchanged |
| Unknown useful field/full profile gap | Named mapped/rejected/unverified disposition; fullAcceptance=false; no opaque sports JSON |

Capture query plan (all indexed exact keys, source connections sequential):
1.AWS identity/settings and current indexed metadata for exactly three document
paths.2.AWS three bounded current indexed JSON documents (index+two partitions),
joined to current object/index SHA.3.AWS exact normalized actor profile-resource
metadata only; no profile body. Close/rollback AWS.4.Neon identity/settings plus
one exact endpoint+params+object metadata in a read-only snapshot. No Neon SQL
body read is planned. Three conditional object requests then read that one
existing Neon blob: HEAD,GET last4bytes,GET complete. SDK retries are disabled,
request hooks enforce3before-send calls, every body is closed. The HTTP origin
and existing credentials are bound to the frozen branch/bucket/host. No provider
call is permitted.

Decoded-source budget counts SQL body UTF8 bytes and all decoded object bytes
once, plus serialized SELECT metadata conservatively. Physical HTTP bytes and
range bytes have a separate1MiB cap. Both origins share the11/32MiB counters.
Object gzip ISIZE is checked before full GET; actual bounded decode verifies it.
The private0700socket directory must be explicitly supplied; no socket/file
cache outside RAM is created. GET serves trusted same-user IPC; STOP releases RAM
and removes the socket. A capture is claimed durably once before connecting, so
crash/replay cannot silently start a new source pass.

Independent oracles unpack the packed partitions without the production unpack
helper and freeze source row membership and exact native tokens in memory before
import.31fields come from FIELDS.json, never from the mapper at runtime. Source
performance IDs/partition paths/ordinals, all31states, metric exact values,
common columns, registry units/rules and full observation bindings are compared
to direct SQL reads. Expected478547=15437x31 is historical: source count/IDs and
pinned versions must be confirmed, never forced. Only counts/digests/field and
ID-level mismatch diagnostics are saved; no raw row or source value is dumped.

Spatial source expectations are derived independently from the declared direct
data member. Compare every observed parent and ordered cell tuple, grid16x12
only if declared, native units/metres and frame, source actor/side and selected
core cohort. The historical32collections/1344triplets are independently counted.
Useful names/shirts retain their existing qualified gap; this lot cannot claim
full native heatmap fidelity merely because spatial tuples pass.

Candidate phases contain genuine source-derived core facts and the reviewed
sparse observation only. The operational wrapper pre-registers Neon source
metadata with its true storage origin before using the frozen helper; it does
not change normalizer/source lookup/native31 logic. Metadata-only phase receipts
bind source hashes, selectors, normalizer SHA and wrapper SHA. A whole spatial
failure rolls back that phase and preserves core proof as partial. No toy
correction, foreign identity or altered native source body is used in this DB.

Before release, execute guard/empty-PG preparation E2E with no source. Save its
real RED before implementing the missing guard/candidate. Real phases remain
unverified until the approved single capture runs. Every run saves exact command,
input code/spec hashes, local migration output, SQL oracle text, expected/actual
counts/digests, errors and owned database cleanup. The same RAM supports fresh
process repetition; a dead server requires a new authorization, not rereading.

Proposed exact commands are in COMMANDS.md. No capture command is run during
preparation. Suggested commit: `test: qualify native metrics and sparse heatmaps from bounded real sources`.
