# Current RDS sources checked against normalized models

At 02:50 UTC on November 4, 2026, the RDS staging snapshot contained **35,691 profiles, 537 catalog sources, and 1,880 supporting projections** eligible for the relational publisher. Every eligible record was accounted for. No additional catalog or support schema migration was required. The preflight exposed a checksum interpretation error in the worker.

| Input | Evidence | Result |
|---|---|---|
| 537 catalog source files | Every RDS path + stored-byte SHA matched the fully validated source inventory and its local PostgreSQL roundtrip | 537/537, zero changed source bodies fetched |
| 1,880 support projections | One read of the eight supported families, exact stored-body comparison to previously tested HTTP fixtures, and current strict encoder | 1,880/1,880; 1,387,681 compact JSON bytes |
| 35,691 profiles | All 2,804 source paths checked in 88 bounded SQL batches. Recursive SQL returned 34,795 compact JSON bytes of path/type/count observations | 33,792 had current physical pins and fully mapped shapes. The remaining 1,899 used the original logical digest |
| 1,899 historical profile references | Verified compact UTF-8 JSON SHA, content-addressed basename, current indexed document version, and strict catalog encoder | 1,899/1,899, covering 1,864 player, 34 team, and one league reference. 460,374 compact JSON source bytes |
| 128 historical match references | Extra sample checked the same digest contract outside profiles | 128/128; 178,581 compact JSON source bytes |

The worker previously compared each ref SHA with the object's compressed bytes. The original world collector at commit `4a7b08dacc` hashed sorted-key compact UTF-8 JSON **before gzip** and used that digest as the immutable basename and the ref SHA. Across all staged endpoint families, 324,839 references have a digest that differs from the physical object checksum. Every one is in the historical world blob namespace. Only the profile set and listed match sample received individual logical digest validation. The scoped worker fix checks the claimed digest against the precise historical path and the logical content. Other source references retain physical checksum verification and the version-pinned document view.

The local PostgreSQL source-to-typed-profile workflow improved **5/6 → 6/6**. A legitimate historical profile now publishes and clears its queue entry. Wrong namespaces, names, pins and logical content fail closed with no published receipt; valid physical pins still work. An initial implementation replay exposed a missing import, retained under `after-import-failure/`. All source probes used read-only TLS sessions on RDS; no new S3 or provider requests were made. Byte counts denote compact JSON, not total wire traffic.

From the repository root, provision requirements in `/tmp/statarena-publication-test-python`, install `embedded-postgres@18.6.0-beta.19` under `/tmp/statarena-cache-test-tools`, and use the read-only runtime SSM parameter with AWS profile `statarena`. Commands and fixtures are recorded in [the protocol](PROTOCOL.md), [profile](profiles.json), [logical checksum](logical.json), [catalog](catalog.json), [support](support.json), [local baseline](before/results.json), and [final local replay](after/results.json). To rerun the red baseline safely, run the same harness with only the worker's Inputs.read restored to the pre-fix revision in a separate local checkout.

Suggested commit `fix: verify historical staging references against their logical content digest`.
