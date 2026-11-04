# Bootstrap lineage and manifest-only discovery

Registered before implementation: a new manifest-only season/league must be built on a normal resume without `--all` or dirty fixtures. Read the physical source SHA with the actual initial content, and commit its typed metadata receipt atomically with the serving partition. A bad declared hash must leave the partition unpublished and its queued work intact. After the first construction, a partial refresh must preserve the typed prior state and the original bootstrap receipt, even if the obsolete seed pack changes. Never infer that an old typed partition consumed today's source SHA.

Extend the existing complete publisher E2E before changing production code. It uses real disposable PostgreSQL18, captured match data, indexed source documents and fallback reads, then inspects committed typed rows/receipts/queues. A new small typed metadata table requires migration010; never edit applied003–009. Runtime business queries remain unchanged. Existing published production scopes lack historical consumption receipts; they require separately attributed reconciliation, not a fabricated backfill.

Exact commands: `node docs/verification/aws-rematerialize-20261104/run.mjs bootstrap-before`, then the same command with `bootstrap-after`. Each phase retains results.json, worker.log and postgres.log with setup, inputs, expected/actual checks and exact rerun command. Expected pre-change failure is the missing receipt table and missed automatic manifest-only scope. Require all existing transactional/source-status/type/lease/capacity regression cases after implementation, including the obsolete-pack fast path and least-privilege installation.

Suggested commit: `fix: discover manifest-only scopes and pin initial serving sources`.
