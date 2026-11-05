# Real normalizer receipt admission v2 — before implementation

The original9ec803transport,21+9local evidence and failed real preflight remain
unchanged. This separate adapter changes source-receipt admission and its explicit
version/bindings only. Native COPY, ownership/dependencies,106control mappings,
row/buffer/metadata limits, monotone sequence reservation, exact target prefix,
target counters/clocks, rollback/resume/no-op and native94guard remain unchanged.

Cause: frozen real normalizer.hashed applies normalized() first, tagging every
int/Decimal/float as {number:canonical_decimal}. The local-fixture hasher retains
ordinary JSON numbers. Thus source_document_count in the input manifest and
generation/fixture/performance counts in the report need the real producer's
preimage. The final sealed object contains only two SHA strings; its shape is
shared but its report/input fingerprints must already be correct. The concrete
core's expected input3fd1ff..., report5a063182..., sealcf7683... are independently
recovered from the frozen producer code and immutable fresh core no-op evidence.

No source row, checkpoint, counter, selector, timestamp or source ledger may be
rewritten to make this admission pass. Calling the frozen producer's pure hash
functions verifies its format; it does not normalize or mutate the stored data.

Source contract (closed current core only): exact producer/model/version,
source checkpoint/native94/31evidence, one core run1/g2/sid2, binding and selector
fingerprints from the real fresh no-op, expected report, two exact document
path/SHA memberships, parameters{}, counters full_acceptance=false/local_only=true/
source_document_count=2. This local-only source counter describes the frozen local
producer; regenerated real target counters remain local_only=false.

Before new code, these CLI/E2E outcomes are fixed:

| Workflow / corruption | Expected outcome |
|---|---|
| Missing new adapter | Genuine missing-file RED, no driver/SQL/socket/process |
| Default CLI with poisoned environment | Offline plan,0connections/COPY/nextval |
| Owned structural metadata fixture only | Pure receipt-structure validation; explicit locally invented metadata, no real producer/source/native/RDS acceptance |
| Plain-JSON input/report hashes or wrong seal | SOURCE_RECEIPT refusal |
| Changed run ID/mode/status/version/code/error or parameters | SOURCE_RECEIPT refusal |
| Missing/extra/altered counters or boolean-as-count | SOURCE_RECEIPT refusal |
| Unknown checkpoint/binding/report key, source ID/phase/key mismatch | SOURCE_RECEIPT refusal |
| Coherently rehashed unknown selector/report/input | SOURCE_RECEIPT refusal against the separately frozen expected contract |
| Missing/unequal/naive four source transaction clocks | SOURCE_RECEIPT refusal |
| Wrong snapshot status/version/priority/cutoff/ID/generation/key | SOURCE_RECEIPT refusal |
| Wrong/missing/duplicate/extra source document membership | SOURCE_RECEIPT refusal |
| Structural metadata passed as real pair/acceptance | BINDING refusal before driver/socket, never a compatibility alias |
| Frozen real source preflight | Exact native94source acceptance,31source proof binding and phase admission;0COPY/nextval/business writes; root alone supplies real RDS credentials/release |

Pure structural fixtures intentionally imitate only the receipt serialization
format and use fixture:document paths and synthetic timestamps. Their origin is
owned_local_receipt_metadata; they contain no native tables, source acceptance or
RDS authority. Actual CLI children with driver/DNS/process tripwires validate
positive and negative cases. These are E2E CLI contracts, not post-code unit tests.
The exact same admission function consumes real SQL metadata only after the real
pair/contract/provenance/native bindings are separately checked.

The actual source inspect order is audited in AUDIT.md. Real source receipts also
must have exactly the accepted run/snapshot set; every phase requires one run,
each document link belongs to the exact snapshot, the numeric types and all closed
keys are checked, four clocks equal the source transaction clock, and native94
bytes remain exact. Dataset membership hashes use the same pinned normalizer
hasher. Selector preimages include profile lookup metadata not fully persisted in
SQL: their exact fingerprint is therefore bound to the immutable real fresh
core no-op, which recomputed that selector from frozen RAM with the actual producer.
No new RAM/cloud/PG reads are authorized by this preparation.

Pilot bounds remain500k/table,2Mtotal,64phases,1MiBrow/payload,16MiBbuffers,
32MiBmetadata,1000rows/batch,8s SQL/1s locks; current concrete core happens to be
one phase. This is not a final production capacity restriction or full-data
acceptance. Source actor gaps/spatial/detailed families remain visible and open.
Every run archives exact inputs/hashes/command/expected/actual/logs and0external
actions. ROOT owns separate real preflight/apply ledgers and independent readback.

Suggested commit: `fix: admit the frozen real normalizer receipt format`.
