# Preparation stopped after the absent-publisher RED

Suggested commit: `test: specify Pro V1 publisher gates and preserve missing CLI red`.

The real isolated Python CLI invocation of dashboard/scripts/orion_pro_publish.py --help returned2 because the file does not exist. Expected usable CLI help was exit0. The test remains **fail/RED**, with expectedPreCodeRedObserved=true; it is not converted into a passing publisher test.

Receipt: [result.json](runs/20261105T002630073522Z-publisher-absent-red/result.json), [stderr](runs/20261105T002630073522Z-publisher-absent-red/stderr.log). Exact rerun:

```sh
python3 docs/verification/orion-pro-publisher-20261105/missing_publisher_gate.py --label publisher-absent-red
```

No PostgreSQL, HTTP, source RAM/body, SQL, publisher, migration or remote action ran. All pinned code/model/012/013/old guard checksums remained unchanged. No014 exists. The helper is absent; model107 remains pending and unused. P01–P29 are explicitly unexecuted.

The proposed first publisher only materializes match_summary/competition_summary for the existing four V1 routes. It must consume already admitted published revisions, explicit engagements and honest coverage; it cannot promote drafts in place, invent source facts/engagements or publish an empty edition by omitting useful draft input. The inspected normalizer still creates draft matches. No native detail107 or new V1 field is included.

Two concrete grant refinements are documented in [PROTOCOL.md](PROTOCOL.md): generated baseline grants do not give DELETE on dirty_editions or direct EXECUTE of validate_aggregation_build. Keep dirty hints/watermarks instead of deleting/resetting them; validate ready through the existing deferred trigger. Actual remote ACLs were not inspected. This does not modify the frozen earlier publisher proposal or any grant.

[FAILURE_MATRIX.md](FAILURE_MATRIX.md) / JSON defines30 intended cases: admission, summaries/states, frozen V1 dg/cg/closure, shared A/B and independent C, no-op before begin_generation, ready-orphan retry, crash/atomic pointer rollback, concurrent workers, newer dirty watermark and writer/runtime privileges. The future local subclass must suppress ReaderFixture's hand-built outputs rather than accepting its build/publish shortcuts as a production publisher oracle; old fixtures stay immutable.

Budget proposed to ROOT in [LOCAL_BUDGET.md](LOCAL_BUDGET.md): one owned PG18.6 and one Bun API,3 editions/5 initial matches, at most2 publisher workers/5 connections,200 HTTP and1500 operational SQL per run,5000 typed rows, bounded fault/race cases, aim5 minutes/hard stop10 minutes. First complete pre-code workflow RED plus at most one setup correction; no publisher implementation authorization is inferred. No campaign was launched.

Work stops here pending ROOT's review of protocol, admission details and local budget. Guard19/19, existing frameworks/artifacts, model, normalizer,012/013, Git/CI/WORKLOG and deployments remain untouched.
