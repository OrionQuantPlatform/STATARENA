# Publisher workflow harness — bounded setup RED

Suggested commit: `test: prepare bounded PostgreSQL publisher workflow before implementation`.

Status: **setup failed; stop for ROOT review**. The authorized first run plus one brief setup correction are exhausted. No product publisher was created, no API started, and this phase did not reach its new absent-CLI gate. The previous cheap missing-CLI RED remains historical evidence only. Neither setup failure is a successful publisher test.

## Exact commands and receipts

From the repository root, with existing PG18.6 binaries at `/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin`, existing Python dependencies at `/tmp/statarena-publication-test-python`, local Bun and dashboard dependencies:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-publisher-20261105/publisher_workflow.py --label owned-pg-precode-red
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-publisher-20261105/publisher_workflow.py --label owned-pg-precode-red-setup-corrected
```

These are reproduction commands, **not authorization for an additional run**. The absent product path is `dashboard/scripts/orion_pro_publish.py`. The harness, synthetic fixture, metadata oracles, real API launcher, guarded worker launcher and30 future workflow cases were written before any publisher implementation.

| Run | Expected | Actual | SHA256 of result.json |
|---|---|---|---|
| `runs/20261105T010437283112Z-owned-pg-precode-red` | Owned schema/typed setup, five setup gates, then one real absent-CLI RED | Setup CHECK012 rejected fixture enum `bench`; API/CLI not reached;1.712s including cleanup | `103af699f816356b6ba5337664c7715b802421723672ed0137158ddba8d243fe` |
| `runs/20261105T010537210224Z-owned-pg-precode-red-setup-corrected` | Same, with native `unused_substitute`/played=false fixture | Input oracle returned successfully; snapshot identifier guard then rejected valid `football.match_h2h_entries`; API/CLI not reached;1.934s including cleanup | `b04ef07c335989fa43739820f79b17e5ddf63520a20dce9f35e3f4af105e7a07` |

Both immutable run directories contain exact input code/model/SQL copies and hashes, commands, PostgreSQL logs, SQL type/digest traces, result and cleanup. No dotenv, numbered copies, real source payloads, credentials or DSN appear in argv. libpq emitted a harmless warning that `/dev/null` is not a regular password file; no credential file was supplied.

## What was observed

Both runs started one owned loopback PG18.6 (`server_version=180006`), applied exact approved012/013, compact bootstrap and unchanged role grants, then stopped and removed the owned database directory. The second receipt verifies exact journal hashes and bootstrap identity:

- Model103/94 active: `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`.
-012: `f255868599c72d69f40f575a919045325ea1093a00fe4f5a6b96eae9f2c49f65`.
-013: `85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968`.

The second run independently verified5 typed matches A3/B1/C1, date/null/status and final score0/null states, explicit team engagements and distinct squad counts A1/B2/C1. The extra B observation is an unused substitute with played=false. ReaderFixture's three build hooks and one publish hook were suppressed; there were zero aggregation builds and publication versions. Dataset generation3 and catalogue generation2 remained distinct. This is input setup evidence under the fixture owner, not evidence that a publisher ran as writer or that HTTP products were correct.

Both machine receipts honestly record0 passed workflow cases,0 failed workflow cases and30 unverified cases because setup failed before P01 could complete. HTTP requests and publisher invocations are0. First run operational SQL reservations0; second run1 (the application-name transition). PostgreSQL independently logged180 and213 fixed setup client commands respectively; no operational command executed after the second transition. SQL/function/type/HTTP/deadline/capability/publication cases beyond setup remain unverified. Typed-row cardinality checks, actual writer/runtime ACL probes, main/two-worker8s/1s cancellation probes, source-access tripwire calibrations and API behavior were not reached and are not claimed passed.

## Concrete blocker and next review

`publisher_oracles.snapshot()` validates trusted model identifiers with `(ingest|football|analytics)\.[a-z_]+`. Static comparison with all94 active model names shows that only `football.match_h2h_entries` is rejected: its valid name contains digits. This assertion runs before the UNION query, explaining the empty AssertionError and absence of any snapshot SQL in the second trace. The next minimal correction is a trusted identifier pattern allowing digits after the first table-name character; it has deliberately not been applied or rerun within the exhausted setup budget.

ROOT should review this guard and the proposed CLI/admission/barrier contracts plus unexecuted future oracles before authorizing further local work. No source acceptance, full normalization, publisher functionality, real-source fidelity, deployed behavior,014/107 or cloud result follows from this fixture setup. The frozen guard19/19, original publisher preparation artifacts, model, migrations, source framework and other products were untouched. Both receipts report `sourceChangesDuringRun=[]` and complete PG/API/worker cleanup.

`WORKFLOW_CHECKSUMS.json` freezes the current harness/review documents and both complete new run directories. Historical run bytes are retained; no logs or receipts were rewritten to turn either failure green.
