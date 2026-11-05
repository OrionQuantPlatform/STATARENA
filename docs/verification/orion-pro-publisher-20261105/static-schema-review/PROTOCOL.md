# Static publisher harness contract review

Suggested commit: `docs: audit publisher harness against the sealed Pro schema`.

ROOT authorizes a static review only after the three preserved setup runs. No PostgreSQL, HTTP, publisher, provider/source payload, cloud, Git/CI/WORKLOG or old artifact is executed or modified. All new output stays in this directory. The148 files pinned by `../THIRD_PRECODE_CHECKSUMS.json` remain unchanged.

The baseline is the canonical103-table model,94 active tables/1709 active columns, exact012/013 and the four frozen V1 readers. Audit the complete publisher harness, TypedInputs, ReaderFixture and inherited PilotWorkflow helpers. Separate inherited methods suppressed/unreachable in this workflow from actual setup/future workflow paths. Inventory every Python string-key subscript, tuple subscript, SQL execute site and typed insert/replace/row call before proposing changes. Compare real table columns, PKs, FKs, unique indexes, CHECK/enum values, selective intervals and DTO shapes; do not treat a missing surrogate as a schema gap.

Expected failure modes include: nonexistent row keys or SQL columns; wrong composite PK; invalid enum; a legal value that contradicts another typed fact; stale collection/alias/profile selection; wrong0/null/empty/absent state; unsafe model identifier; wrong SQL result index/DTO path; an oracle passing only a count while claiming native fidelity. A static scanner is an inventory/name check, not a SQL engine, theorem prover, E2E pass or full source-acceptance result. Every dynamic/unresolved site must receive an explicit manual classification.

Deliver: exact source hashes and model/DDL counts; complete machine-readable access/SQL inventory; concrete diagnostic matrix with before/after proposals and required E2E observations; typed coverage contract bound to its real five-column PK plus data_revision/match_revision_id and half-open interval; unapplied changes only. No fourth PG run follows from this review. ROOT reviews the entire proposal before any harness amendment or execution.

Rerun the static inventory only:

```sh
python3 docs/verification/orion-pro-publisher-20261105/static-schema-review/review.py
```

This command parses and hashes code/model/SQL as text. It does not import any application/fixture/publisher module, connect to a database, start a process, or access a network. Its generated inventory is supporting evidence for the separately documented manual review, not an automatic approval.
