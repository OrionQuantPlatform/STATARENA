# Copy the retained 103 core into the approved 107 schema

The existing 94-relation source and its native oracle remain frozen. The target must have the exact approved 012–017 chain, 98 active relations, 1,829 columns and 447 foreign keys. The four new detail tables stay empty for this core transfer. The 71 added columns on shared tables use their exact typed defaults (NULL, unrecorded, or the constant lineups). Their data are qualified later from independent source observations. This step cannot certify native detail coverage or publish a build.

The native COPY continues to name only source columns, with its 106 existing control-component maps. PostgreSQL reads the two original float8 coordinates into target numeric from their exact round-trip text. The inverse oracle casts those two coordinates back to float8 only after it verifies that the numeric text exactly represents a supported source float. Reject negative zero and nonfinite source coordinates explicitly before COPY: numeric cannot attest their exact float8 representation. Preserve NULL and ordinary zero separately. Verify that neither widened nullability can introduce values absent from the source.

Migration016/017 adoption is atomic under the existing migration, generation and serving leases. Check the exact previous journal, schema, 67 sequences, view OID/ACL/type and preserved state before writing. Use the approved scripts only, recording their actual journal clocks and hashes. An independent connection classifies the committed state; a lost acknowledgement is never an automatic retry. No user data is removed, no sequence reset or ACL bypass. This lot adds no changes to the approved model and no new AWS infrastructure. A future 018 validator/index change has its own review and policy.

| Workflow written before the adapter | Expected result |
| --- | --- |
| Missing adapter, offline with poisoned PG settings | RED and no connection; no implicit target. |
| Install exact old source and target, force abort after 016 | Original projected data, journal, sequence values, protected view and catalogue restored. |
| Commit 016/017 then independently reread | Exactly the approved 98/1829/447, original clocks preserved, same view/OID/ACL and 67 sequences. Exact reapply is a no-op. |
| Tamper an overlay column or leave a foreign journal version | Refuse before transfer or migration writes, preserve original state. |
| Source and target use ordinary runtime/ingest actors | Read-only source; ordinary COPY, native checks and deferred commits on target; no sequence-value SELECT by the copy actors. |
| COPY both compact native phases using unchanged column lists | 40 appearances and 1240 metric states, matching old 91 business relation vectors after inverse control and coordinate mapping; no cloud, source-body, JSON staging or new column values. |
| Validate distinct original coordinate states | NULL, +0, and the precise nonzero values survive. Refuse a nonrepresentable float before transfer. A numeric with invented digits must not pass a float-only readback. |
| Fresh readback and replay | Three controls separate, target child tables empty, old source and legacy sentinel unchanged, no new COPY or nextval on replay. |

The owned test is bounded to one loopback PG18.6 cluster, two fixture databases, at most five clients, 180 seconds, 1 GiB owned space and 64 MiB evidence. It records exact setup, fixture SQL and source pins, command, case outputs, real COPY/SQL and cleanup. It does not connect to actual RDS or reopen the retained source. The exact post-018 runtime transport and its real endpoint release remain separate gates.

Suggested commit: `feat: qualify the retained core transfer into the approved native schema`.
