"""Owned native PG/real-CLI/HTTP execution context, authored before adapters."""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
SCRIPTS = ROOT / "dashboard/scripts"
sys.dont_write_bytecode = True
sys.path[:0] = [str(BASE), str(ROOT / "tests"), str(SCRIPTS), str(ROOT / "docs/verification/orion-pro-pilot-20261104"),
               str(BASE.parent / "product-campaign"), "/tmp/statarena-publication-test-python"]
from orion_e2e_process import run_bounded
from workflow_budget import SharedBudget, connection_factory
from runtime_fixture import RealFixture, POLICY, FIXTURE_VERSION
from typed_oracle import TypedOracle, tagged, compact

MODEL = ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
PG_BIN = Path("/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin")
HELPERS = {"admit": SCRIPTS / "orion_pro_admit_real.py", "publish": SCRIPTS / "orion_pro_publish_real.py"}
ADMISSION_TRANSFORM = "real_core_four_readers_admission_v1"
BOUNDS = {"seconds": 600, "sql": 6000, "http": 200, "typedRows": 20000, "ownedDiskBytes": 1024**3,
          "evidenceBytes": 96 * 1024**2, "workers": 2, "connections": 5, "maxBufferedRows": 1000}
OPTIONS = "-c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000 -c timezone=UTC -c datestyle=ISO,YMD -c extra_float_digits=3"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashed(value):
    return hashlib.sha256(compact(value).encode()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def minimal_env():
    return {k: os.environ[k] for k in ["PATH", "HOME", "USER", "LANG", "LC_ALL"] if k in os.environ}


class StreamingOracle(TypedOracle):
    """Independent pre-code closure oracle without the old5000 local cutoff."""
    def rows(self, table, where="TRUE", params=(), generation=None):
        spec = self.tables[table]
        predicates, values = ["(" + where + ")"], list(params)
        if "recorded_from_gen" in spec["columns"]:
            predicates.append("r.recorded_from_gen<=%s AND (r.recorded_to_gen IS NULL OR %s<r.recorded_to_gen)")
            values += [generation, generation]
        if "is_canonical" in spec["columns"]:
            predicates.append("r.is_canonical")
        if "is_deleted" in spec["columns"]:
            predicates.append("NOT r.is_deleted")
        result = []
        for row in self.conn.execute("SELECT r.* FROM " + table + " r WHERE " + " AND ".join(predicates), values):
            result.append(row)
            assert len(result) <= BOUNDS["typedRows"]
        # Psycopg's concrete typed values, not a producer JSON decoder.
        names = list(spec["columns"])
        self.queries += 1
        return [dict(zip(names, row)) for row in result]


class Runtime:
    def __init__(self, run, release, deadline):
        self.run, self.release_doc, self.deadline = Path(run), release, deadline
        self.database = "postgres"
        self.serial = self.http_serial = 0
        self.children, self.invocations, self.requests, self.old_http = [], [], [], {}
        self.pg = self.db = self.api = None
        self.api_streams, self.cleanup = [], {}
        self.ram_gets = self.cloud_calls = 0
        self.admission_receipt = None
        self.overrides = []
        self.resources = []
        self.resource_tick = 0.0
        self.budget = SharedBudget(self.run / "budget.json", create=True)
        state = self.budget.read()
        state["deadlineEpoch"] = time.time() + max(0, deadline - time.monotonic())
        state["limits"].update(sql=BOUNDS["sql"], http=BOUNDS["http"], typedRows=BOUNDS["typedRows"])
        save(self.budget.path, state)
        self.input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in self.code_inputs()}

    def code_inputs(self):
        return [MODEL, *[p for p in HELPERS.values() if p.exists()], *sorted(BASE.glob("*.py")), BASE / "FAILURE_MATRIX.json", BASE / "CONTRACT.md",
                *[ROOT / "dashboard/backend/migrations" / n for n in ["012_orion_pro_domain.sql", "013_orion_pro_integrity.sql", "014_orion_pro_membership_nonnull.sql"]],
                *[SCRIPTS / n for n in ["orion_pro_normalize.py", "orion_pro_integrity.py", "orion_pro_schema.py", "orion_pro_migrate.py"]],
                *[ROOT / "dashboard/backend/services" / n for n in ["orion-pro.js", "postgres.js", "database-connection.js", "metrics.js", "cache-policy.js", "cache.js", "relational-match.js", "relational-support.js", "relational-catalog.js", "cdn.js", "relational-core.js", "partition-wire.js", "catalog-model.json", "support-model.json"]]]

    def check(self):
        self.budget.check()
        assert time.monotonic() < self.deadline, "Absolute runtime campaign deadline"
        if self.pg:
            proof_bytes = sum(p.stat().st_size for p in self.run.rglob("*") if p.is_file())
            assert proof_bytes <= BOUNDS["evidenceBytes"]
            if self.pg.root.exists() and time.monotonic() - self.resource_tick >= .5:
                self.resource_tick = time.monotonic()
                value = run_bounded(["du", "-sk", str(self.pg.root)], deadline=min(self.deadline, time.monotonic() + 2), env=minimal_env())
                allocated = int(value.stdout.split()[0]) * 1024
                self.resources.append({"remainingSeconds": round(self.deadline - time.monotonic(), 3), "ownedDiskBytes": allocated, "evidenceBytes": proof_bytes})
                assert allocated <= BOUNDS["ownedDiskBytes"]
                save(self.run / "resources.json", self.resources)

    def command(self, argv, *, name, cleanup=False):
        deadline = min(time.monotonic() + 30, self.deadline + 20 if cleanup else self.deadline)
        result = run_bounded([str(v) for v in argv], deadline=deadline, cwd=ROOT, env=minimal_env())
        prefix = f"{len(self.pg.commands):03d}-{name}"
        (self.run / (prefix + ".stdout.log")).write_text(result.stdout)
        (self.run / (prefix + ".stderr.log")).write_text(result.stderr)
        self.pg.commands.append({"argv": [str(v) for v in argv], "exitCode": result.returncode, "prefix": prefix})
        save(self.run / "commands.json", self.pg.commands)
        assert result.returncode == 0, name
        return result

    def setup(self):
        import psycopg
        from harness import LocalPostgres
        from orion_pro_migrate import bootstrap
        from orion_pro_integrity import role_grants_sql
        self.psycopg = psycopg
        tempfile.tempdir = "/tmp"
        self.pg = LocalPostgres(PG_BIN, self.run)
        self.command([PG_BIN / "initdb", "-D", self.pg.data, "--auth=trust", "--no-locale", "--encoding=UTF8"], name="initdb")
        cert, key = self.pg.data / "server.crt", self.pg.data / "server.key"
        self.command(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes", "-days", "2", "-keyout", key,
                      "-out", cert, "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1"], name="tls")
        key.chmod(0o600)
        with (self.pg.data / "postgresql.conf").open("a") as out:
            out.write("\nssl=on\nssl_cert_file='server.crt'\nssl_key_file='server.key'\nmax_connections=5\nsuperuser_reserved_connections=0\nmax_locks_per_transaction=1024\nlog_statement='all'\nlog_parameter_max_length=0\nlog_parameter_max_length_on_error=0\nlog_line_prefix='[%p] app=%a '\n" + "statement_timeout=8000\nlock_timeout=1000\nidle_in_transaction_session_timeout=5000\n")
        self.command([PG_BIN / "pg_ctl", "-D", self.pg.data, "-l", self.run / "postgres.log", "-o",
                      f"-h 127.0.0.1 -p {self.pg.port} -k {self.pg.socket_dir}", "-w", "start"], name="postgres-start")
        self.pg.started = True
        self.cert = cert
        self.db = self.connect(os.environ.get("USER", "postgres"))
        assert self.db.info.server_version == 180006
        for actor in ["statarena_admin", "statarena_ingest", "statarena_runtime"]:
            self.db.execute("CREATE ROLE " + actor + " LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS")
        self.db.execute("ALTER DATABASE postgres OWNER TO statarena_admin")
        self.db.close()
        self.db = self.connect("statarena_admin")
        self.model = json.loads(MODEL.read_text())
        self.tables = {t["qualified_name"]: t for s in self.model["schemas"] for t in s["tables"] if t["phase"] != "models"}
        with self.db.transaction():
            artifacts = []
            for version, name in [("012", "012_orion_pro_domain.sql"), ("013", "013_orion_pro_integrity.sql"), ("014", "014_orion_pro_membership_nonnull.sql")]:
                path = ROOT / "dashboard/backend/migrations" / name
                sql = path.read_text()
                self.db.execute(sql, prepare=False)
                self.db.execute("INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)", (version, sha(path), self.release_doc["codeCommit"]))
                artifacts.append((version, path, sql))
            boot = bootstrap(self.db, self.model, artifacts[:2])
            self.db.execute(role_grants_sql(self.model, ingest_role="statarena_ingest", runtime_role="statarena_runtime"), prepare=False)
        self.fixture = RealFixture(self.db, self.pg.dsn, self.run, psycopg)
        self.fixture.bootstrap_code = boot["codeSha256"]
        self.fixture.prepare_raw()
        self.fixture.clear_coordinates()
        self.expected_matches = self.fixture.expected
        self.raw_match_rows = self.fixture.raw_match_rows
        self.expected_labels = self.fixture.expected_labels
        self.expected_played = self.fixture.expected_played
        self.bench_pair = self.fixture.bench_pair
        self.immutable_match_values = [k for k in self.tables["football.matches"]["columns"] if k not in {
            "revision_id", "recorded_from_gen", "recorded_to_gen", "publication_state", "data_revision", "updated_at", "transform_version", "transform_code_sha256", "provenance_kind"}]
        self.oracle = StreamingOracle(self.db, self.model)
        self.initial_native31 = self.native31()
        self.initial_source_identity_facts = self.source_identity_facts()
        self.core_native = self.native_tables()
        self.source_generation = self.fixture.data_generation
        self.source_epoch_sha = hashed(self.core_native)
        self.expected_catalogue_counts = {"table": 94, "column": 1709, "foreignKey": 431, "constraint": 2475, "view": 46, "sequence": 67}
        self.marker = {"kind": "owned_real_publication_endpoint_v1", "environment": "owned_local_tls", "host": "127.0.0.1", "hostaddr": "127.0.0.1",
            "hostname": "127.0.0.1", "port": self.pg.port, "database": self.database, "actor": "statarena_ingest", "ownedRoot": str(self.pg.root),
            "caPath": str(cert), "caSha256": sha(cert), "postmasterStartedAt": self.db.execute("SELECT pg_postmaster_start_time()").fetchone()[0].isoformat()}
        save(self.run / "endpoint.json", self.marker)
        self.admission_transform = ADMISSION_TRANSFORM
        self.admission_code_sha = sha(HELPERS["admit"]) if HELPERS["admit"].exists() else None
        self.expected_coverage_sets = self.coverage_sets()

    def connect(self, actor):
        import psycopg
        factory = connection_factory(psycopg, self.budget, self.run / "main-sql.jsonl", phase=lambda: "operational", owned_port=self.pg.port, role=actor)
        return factory.connect(host="127.0.0.1", hostaddr="127.0.0.1", port=self.pg.port, dbname=self.database, user=actor,
                               sslmode="verify-full", sslrootcert=str(self.cert), autocommit=True, options=OPTIONS,
                               application_name="real_publication_harness")

    def help(self, stage):
        result = run_bounded([sys.executable, "-I", str(HELPERS[stage]), "--help"], deadline=min(self.deadline, time.monotonic() + 5), cwd=ROOT, env=minimal_env())
        (self.run / (stage + "-help.stdout.log")).write_text(result.stdout)
        (self.run / (stage + "-help.stderr.log")).write_text(result.stderr)
        return result

    def native_tables(self):
        sql = " UNION ALL ".join("SELECT '" + name + "',count(*),md5(coalesce(string_agg(md5(ROW(t.*)::text),'' ORDER BY md5(ROW(t.*)::text)),'')) FROM " + name + " t" for name in self.tables)
        return {r[0]: {"rows": r[1], "nativeDigest": r[2]} for r in self.db.execute(sql)}

    def state(self):
        self.check()
        names = [r[0] for r in self.db.execute("SELECT schemaname||'.'||sequencename FROM pg_sequences WHERE schemaname IN ('ingest','football','analytics') ORDER BY 1")]
        assert len(names) == 67 and all(re.fullmatch(r"(?:ingest|football|analytics)\.[a-z_][a-z0-9_]*", n) for n in names)
        sequences = list(self.db.execute(" UNION ALL ".join("SELECT '" + n + "',last_value,is_called FROM " + n for n in names)))
        return {"tables": self.native_tables(), "sequences": sequences}

    def native31(self):
        return self.db.execute("SELECT count(*),md5(coalesce(string_agg(md5(ROW(v.*)::text),'' ORDER BY md5(ROW(v.*)::text)),'')) FROM football.player_match_metric_values v").fetchone()

    def source_identity_facts(self):
        all_tables = self.native_tables()
        return {n: all_tables[n] for n in ["football.players", "football.teams", "ingest.sources", "ingest.source_datasets", "ingest.source_documents", "ingest.source_records"]}

    def selected(self, table, columns):
        return [tuple(r[k] for k in columns) for r in self.fixture.at(table)]

    def selected_count(self, table, predicate):
        return len(self.fixture.at(table, predicate))

    def selected_player(self, pair):
        rows = self.fixture.at("football.match_players", "match_id=%s AND player_id=%s", pair)
        assert len(rows) == 1
        return rows[0]

    def match(self, mid):
        rows = self.fixture.at("football.matches", "id=%s", (mid,))
        assert len(rows) == 1
        return rows[0]

    def match_alias(self, mid):
        rows = self.fixture.at("ingest.public_aliases", "route_kind='match' AND match_id=%s", (mid,))
        assert len(rows) == 1
        return rows[0]

    def dirty(self):
        return list(self.db.execute("SELECT competition_season_id,generation,competition_season_revision_id FROM ingest.dirty_editions ORDER BY 1"))

    def catalogue(self):
        row = self.db.execute("""SELECT
          (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind='r'),
          (SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped),
          (SELECT count(*) FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname IN ('ingest','football','analytics') AND k.contype='f'),
          (SELECT count(*) FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname IN ('ingest','football','analytics')),
          (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind='v'),
          (SELECT count(*) FROM pg_sequences WHERE schemaname IN ('ingest','football','analytics'))""").fetchone()
        return {"counts": dict(zip(["table", "column", "foreignKey", "constraint", "view", "sequence"], row))}

    def independent_closures(self):
        self.fixture.refresh()
        self.oracle.cache.clear()
        return {str(e["id"]): self.oracle.closure(e["id"], self.fixture.data_generation, self.fixture.catalog_generation)["sha256"] for e in self.fixture.editions.values()}

    def profile_selections(self):
        self.independent_closures()
        return {str(e["id"]): self.oracle.closure(e["id"], self.fixture.data_generation, self.fixture.catalog_generation)["manifest"]["profileSelections"] for e in self.fixture.editions.values()}

    def coverage_sets(self):
        result = {}
        for mid, match in self.fixture.match_rows.items():
            parent = self.fixture.coverages.get(mid)
            result[mid] = {"state": parent["collection_state"] if parent else "unknown",
                "matchRevisionId": parent["match_revision_id"] if parent else None,
                "dataRevision": parent["data_revision"] if parent else None,
                "key": {k: parent[k] for k in self.tables["ingest.match_coverage"]["primary_key"]["columns"]} if parent else None,
                "shotIds": sorted(str(r["external_shot_id"]) for r in self.fixture.at("football.shots", "match_id=%s", (match["id"],)))}
        return result

    @property
    def expected_engagements(self):
        matches = {r["id"]: r for r in self.fixture.at("football.matches")}
        return {(matches[r["match_id"]]["competition_season_id"], r["team_id"]) for r in self.fixture.at("football.match_teams")}

    def input_body(self):
        self.fixture.refresh()
        editions = []
        for key, edition in self.fixture.editions.items():
            members = [{"matchId": row["id"], "matchRevisionId": row["revision_id"], "publicId": mid,
                        "sourceId": row["source_id"], "sourceRecordId": row["source_record_id"], "publicationState": row["publication_state"]}
                       for mid, row in self.fixture.match_rows.items() if row["competition_season_id"] == edition["id"]]
            editions.append({"editionId": edition["id"], "editionRevisionId": edition["revision_id"], "competitionId": edition["competition_id"],
                             "publicLeagueId": "l_000001", "season": edition["season_key"], "completeUsefulCohort": True, "members": members})
        snapshots = {r[0]: {"snapshotId": r[1], "generation": r[0], "manifestSha256": r[2], "sourcePriorityVersion": r[3]}
                     for r in self.db.execute("SELECT generation,id,manifest_sha256,source_priority_version FROM ingest.dataset_snapshots WHERE status='sealed'")}
        core_sha = hashed(self.core_native)
        body = {"schemaVersion": 1, "kind": "orion_real_publication_owned_fixture_admission_v1", "dataOrigin": "owned_source_free_fixture",
            "fixtureContractSha256": sha(BASE / "runtime_fixture.py"), "sourcePolicy": POLICY,
            "modelSha256": sha(MODEL), "representationVersion": "summary-v1-shots-v1", "dependencyScheme": "orion-four-readers-dependencies-v1",
            "sourceReconciliationSha256": core_sha, "sourceFieldMatrixSha256": sha(BASE / "SOURCE_FIELD_MATRIX.json"),
            "transport": {"origin": "owned_source_free_fixture", "coreCheckpointSha256": core_sha, "sourceNative94Sha256": core_sha,
                "sourceNative31Sha256": hashed(list(self.initial_native31)), "sourceTargetMappingSha256": core_sha,
                "targetNative94ReadbackSha256": core_sha, "targetNative31ReadbackSha256": hashed(list(self.initial_native31)),
                "sourceProducerVersion": FIXTURE_VERSION, "sourceProducerSha256": sha(BASE / "runtime_fixture.py")},
            "publisher": {"commit": self.release_doc["codeCommit"], "contentSha256": sha(HELPERS["publish"]), "environmentSha256": hashed(self.input_hashes),
                "transformVersion": "orion_pro_publish_real_v1", "metricsContractVersion": "orion_pro_four_readers_v1"},
            "admissionProducer": {"commit": self.release_doc["codeCommit"], "contentSha256": sha(HELPERS["admit"]), "transformVersion": ADMISSION_TRANSFORM},
            "admissionReceiptSha256": self.admission_receipt, "dataset": snapshots[self.fixture.data_generation], "catalogue": snapshots[self.fixture.catalog_generation],
            "sourceInput": snapshots[self.source_generation], "sourceInputEpochSha256": self.source_epoch_sha,
            "endpoint": copy.deepcopy(self.marker), "editions": editions, "proofs": {"minimumSource": copy.deepcopy(self.fixture.minimum_source),
                "coverage": self.coverage_sets(), "labels": [{"matchId": k[0], "side": k[1], "labelSha256": hashed(tagged(v)),
                "teamId": next(r["team_id"] for r in self.fixture.at("football.match_teams", "match_id=%s AND side=%s", k)),
                "sourceRecordId": self.fixture.ids["record"], "state": "string" if v is not None else "null"} for k, v in self.expected_labels.items()]},
            "fullAcceptance": False}
        for mid, expected in self.fixture.expected.items():
            proof = body["proofs"]["minimumSource"][mid]
            present = expected["scoreObserved"]
            proof["finalScoreObservation"] = {"present": present, "scope": "final_without_shootout" if present else None,
                "home": {"state": "absent" if not present else "null" if expected["home"] is None else "number", "sha256": hashed(tagged(expected["home"]))},
                "away": {"state": "absent" if not present else "null" if expected["away"] is None else "number", "sha256": hashed(tagged(expected["away"]))}}
            proof["shootoutObservation"] = {"present": expected["homePenalty"] is not None or expected["awayPenalty"] is not None,
                "homeSha256": hashed(tagged(expected["homePenalty"])), "awaySha256": hashed(tagged(expected["awayPenalty"]))}
        for change in self.overrides:
            change(body)
        return body

    def refresh_input(self):
        self.fixture.refresh()

    def start(self, stage, *, mode=None, patch=None, raw=None, endpoint_patch=None, env=None, barrier=None, fault=None,
              environment="owned_local_tls", release_issue=None, offline=False, tripwire=False):
        self.check()
        active = [x for x in self.children if x["process"].poll() is None]
        assert len(active) < 2
        worker = next(w for w in ["worker1", "worker2"] if w not in {v["worker"] for v in active})
        self.serial += 1
        stem = self.run / f"cli-{self.serial:03d}"
        receipt, events = stem.with_suffix(".json"), Path(str(stem) + "-events.jsonl")
        local_env = minimal_env()
        local_env.update(STATARENA_TEST_DATABASE="1", ORION_REAL_E2E_RUN=str(self.run), ORION_REAL_E2E_STAGE=stage,
                         ORION_REAL_E2E_WORKER=worker, ORION_REAL_E2E_EVENTS=str(events))
        local_env.update(env or {})
        flags = []
        if not offline:
            body = self.input_body()
            if patch:
                patch(body)
            inp = Path(str(stem) + "-input.json")
            inp.write_bytes(raw if raw is not None else (json.dumps(body, sort_keys=True, default=str) + "\n").encode())
            endpoint = self.run / "endpoint.json"
            if endpoint_patch:
                value = copy.deepcopy(self.marker); endpoint_patch(value)
                endpoint = Path(str(stem) + "-endpoint.json"); save(endpoint, value)
            operation = {"kind": "real_publication_owned_operation_release_v1", "scope": "owned_source_free_fixture", "stage": stage,
                "mode": mode or ("apply" if stage == "admit" else "publish"), "helperSha256": sha(HELPERS[stage]),
                "fixtureSha256": sha(BASE / "runtime_fixture.py"), "inputSha256": sha(inp), "endpointSha256": sha(endpoint),
                "sourceReconciliationSha256": hashed(self.core_native),
                "sourceInputEpochSha256": self.source_epoch_sha,
                "campaignReleaseSha256": self.release_doc["releaseSha256"], "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}
            operation_path = Path(str(stem) + "-release.json")
            if release_issue == "release_expired": operation["expiresAt"] = "2000-01-01T00:00:00+00:00"
            if release_issue == "release_wrong_code": operation["helperSha256"] = "0" * 64
            if release_issue == "release_wrong_target_readback": operation["targetReadbackSha256"] = "0" * 64
            if release_issue == "release_reused": operation["consumed"] = True
            save(operation_path, operation)
            flags = ["--environment", environment, "--mode", operation["mode"], "--input", str(inp), "--input-sha256", sha(inp),
                     "--endpoint", str(endpoint), "--endpoint-sha256", sha(endpoint), "--receipt", str(receipt)]
            if release_issue != "release_absent":
                flags += ["--release", str(operation_path), "--release-sha256", sha(operation_path)]
        if barrier or fault:
            control = Path(str(stem) + "-control.json")
            save(control, {"phase": barrier, "fault": fault, "releaseFile": str(stem) + ".release", "timeoutSeconds": 3})
            local_env["ORION_REAL_E2E_CONTROL"] = str(control)
        command = [sys.executable, "-I", str(BASE / "runtime_worker.py"), *flags]
        if tripwire:
            # The worker already physically fences C-driver arguments and all
            # nonowned Python I/O; driver.jsonl separately proves no driver use.
            local_env["ORION_REAL_E2E_REQUIRE_OFFLINE"] = "1"
        out = Path(str(stem) + ".stdout.log").open("w")
        err = Path(str(stem) + ".stderr.log").open("w")
        driver_offset = self.driver_count(worker)
        process = subprocess.Popen(command, cwd=ROOT, env=local_env, stdout=out, stderr=err, start_new_session=True)
        item = {"process": process, "worker": worker, "stage": stage, "stem": stem, "receipt": receipt, "events": events,
                "streams": [out, err], "command": command, "driverOffset": driver_offset}
        self.children.append(item)
        return item

    def driver_count(self, worker):
        path = self.run / (worker + "-driver.jsonl")
        return len(path.read_text().splitlines()) if path.exists() else 0

    def finish(self, child, rejected=False):
        end = min(self.deadline, time.monotonic() + 30)
        while child["process"].poll() is None:
            self.check()
            assert time.monotonic() < end, "Owned CLI child timeout"
            time.sleep(.01)
        for stream in child["streams"]: stream.close()
        path = child["receipt"]
        result = json.loads(path.read_text()) if path.exists() else None
        stdout = Path(str(child["stem"]) + ".stdout.log").read_text()
        stderr = Path(str(child["stem"]) + ".stderr.log").read_text()
        assert "postgresql://" not in stdout + stderr and "postgres://" not in stdout + stderr
        if result is None and stdout.lstrip().startswith("{"):
            result = json.loads(stdout)
        self.invocations.append({"command": child["command"], "exitCode": child["process"].returncode, "receipt": str(path.relative_to(self.run)),
                                 "result": result, "driverCalls": self.driver_count(child["worker"]) - child["driverOffset"]})
        if rejected:
            assert child["process"].returncode != 0 and result and result["status"] in ["rejected", "retry"]
        else:
            assert result is not None and (child["process"].returncode == 0 or result.get("error", {}).get("code") == "COMMIT_ACK_UNKNOWN"), stderr
        return result

    def invoke(self, stage, **kwargs):
        child = self.start(stage, **kwargs)
        result = self.finish(child)
        return child["process"], result

    def reject(self, stage, *, before_driver=False, code=None, **kwargs):
        before = self.state()
        child = self.start(stage, **kwargs)
        result = self.finish(child, rejected=True)
        assert self.state() == before
        if before_driver:
            assert self.driver_count(child["worker"]) == child["driverOffset"]
        if code:
            assert result["error"]["code"] == code
        return result

    def apply_admission(self):
        _, result = self.invoke("admit", mode="apply")
        assert result["status"] in ["admitted", "noop"]
        self.admission_receipt = sha(self.children[-1]["receipt"])
        self.fixture.refresh()
        assert self.native31() == self.initial_native31
        self.expected_coverage_sets = self.coverage_sets()
        return result

    def publish_plan(self):
        _, result = self.invoke("publish", mode="plan")
        assert result["status"] == "planned"
        return result

    def publish(self):
        _, result = self.invoke("publish", mode="publish")
        assert result["status"] in ["published", "noop"]
        return result

    def phase(self, child, phase):
        deadline = min(self.deadline, time.monotonic() + 3)
        while time.monotonic() < deadline:
            self.check()
            if child["events"].exists():
                for line in child["events"].read_text().splitlines():
                    event = json.loads(line)
                    if event.get("phase") == phase:
                        identity = self.db.execute("SELECT usename FROM pg_stat_activity WHERE pid=%s", (event["backendPid"],)).fetchone()
                        assert identity == ("statarena_ingest",)
                        return event
            assert child["process"].poll() is None, "CLI exited before required phase"
            time.sleep(.01)
        raise AssertionError("Missing real CLI phase: " + phase)

    def release(self, child):
        Path(str(child["stem"]) + ".release").write_text("release\n")

    def kill(self, child):
        os.killpg(child["process"].pid, signal.SIGKILL)
        child["process"].wait(timeout=3)
        for stream in child["streams"]:
            if not stream.closed: stream.close()
        self.invocations.append({"command": child["command"], "exitCode": child["process"].returncode, "killed": True})

    def ready_build_ids(self):
        return [r[0] for r in self.db.execute("SELECT id FROM analytics.aggregation_builds WHERE status='ready'")]

    def active_builds(self):
        return list(self.db.execute("SELECT competition_season_id,build_id,catalog_snapshot_id,published_from_gen,representation_version FROM analytics.publication_versions WHERE published_to_gen IS NULL ORDER BY 1"))

    def trace_offset(self):
        return {w: len((self.run / (w + "-sql.jsonl")).read_text().splitlines()) if (self.run / (w + "-sql.jsonl")).exists() else 0 for w in ["worker1", "worker2"]}

    def trace_since(self, offsets):
        return [json.loads(line) for w, offset in offsets.items() for line in ((self.run / (w + "-sql.jsonl")).read_text().splitlines()[offset:] if (self.run / (w + "-sql.jsonl")).exists() else [])]

    def input_hashes_unchanged(self):
        return all(sha(ROOT / name) == value for name, value in self.input_hashes.items())

    def source_accesses(self):
        return [json.loads(line) for p in self.run.glob("*-access.jsonl") for line in p.read_text().splitlines()]

    @contextmanager
    def input_change(self, issue):
        first, unknown = "m_000001", "m_000006"
        def patch(body):
            proofs = body["proofs"]
            source = proofs["minimumSource"]
            if issue == "unresolved_actor": source[first]["unresolvedActorIds"] = ["p_OWN001"]
            elif issue == "wrong_team_name_id": proofs["labels"][0]["teamId"] = self.fixture.ids["teams"][4]["id"]
            elif issue == "missing_name_locator": proofs["labels"][0].pop("sourceRecordId")
            elif issue == "unproved_name_presence": proofs["labels"][0]["state"] = "unverified"
            elif issue == "ignored_available_shootout": source[first]["shootoutObservation"] = {"present": True, "homeSha256": hashed(tagged(4)), "awaySha256": hashed(tagged(3))}
            elif issue == "wrong_final_scope": source[first]["finalScoreObservation"]["scope"] = "regulation"
            elif issue == "absent_score_relabelled_zero": source[unknown]["finalScoreObservation"]["home"] = {"state": "number", "sha256": hashed(tagged(0))}
            elif issue == "infer_midnight_for_unknown": source[unknown].update(timeState="available", kickoffSha256=hashed(tagged(datetime(2026, 11, 4, tzinfo=timezone.utc))))
            elif issue == "coverage_same_count_wrong_ids": proofs["coverage"][first]["shotIds"][0] = "owned_wrong_same_count"
            elif issue == "coverage_wrong_variant": proofs["coverage"][first]["key"]["variant_key"] = "owned:foreign"
            elif issue == "coverage_wrong_revision": proofs["coverage"][first]["matchRevisionId"] = 9223372036854775807
            elif issue == "coverage_stale_key": proofs["coverage"][first]["key"]["recorded_from_gen"] += 1
            elif issue == "shot_wrong_period": proofs["coverage"][first]["periodBindings"] = {"s_000001": "second_half"}
            elif issue == "shot_wrong_actor": proofs["coverage"][first]["actorBindings"] = {"s_000001": self.fixture.ids["players"][2]["id"]}
            elif issue == "infer_metres_or_acting_ltr": source[first].update(sourceFrameState="acting_ltr", sourceXyState="metres_without_proof")
            elif issue == "unmapped_available_field_claimed_observed_null": source[first]["sourceXyState"] = "observed_null"
            elif issue == "derived_input_closure_changed": body["admissionReceiptSha256"] = "0" * 64
            else: raise AssertionError("Unknown declared input mutation: " + issue)
        self.overrides.append(patch)
        try:
            yield
        finally:
            self.overrides.pop()

    def owner_epoch(self):
        self.fixture.refresh()
        self.oracle.cache.clear()
        self.initial_native31 = self.native31()
        self.expected_coverage_sets = self.coverage_sets()
        self.source_generation = self.fixture.data_generation
        self.source_epoch_sha = hashed(self.native_tables())

    @contextmanager
    def fixture_change(self, action, **kwargs):
        # Expected source changes are committed only by this owned test fixture.
        # On an unexpected failure no restoration/extra child is run: cleanup
        # retains the failed receipt and stops the campaign.
        restore = None
        witness = {}
        if action == "minutes_state":
            self.fixture.mutate_minutes(kwargs["kind"])
            restore = lambda: self.fixture.mutate_minutes("null")
        elif action == "resolved_shot_without_performance":
            witness = self.fixture.add_shot_participant()
        elif action in ["profile_priority", "ambiguous_profile"]:
            actor = self.fixture.ids["teams"][0]["id"]
            variant = kwargs.get("variant", "normalized")
            with self.fixture._generation("profile_test_" + variant) as g:
                self.fixture.data_generation = self.fixture.catalog_generation = g
                for row in self.fixture.at("football.team_profile_versions", "team_id=%s", (actor,)):
                    self.fixture._replace("football.team_profile_versions", row, is_canonical=False)
                for i in range(2 if action == "ambiguous_profile" else 1):
                    manual = variant == "manual"
                    values = dict(team_id=actor, observed_at=datetime.now(timezone.utc), is_canonical=True,
                        display_name=None if variant == "null_winner" else "Owned selected profile",
                        profile_context="global" if manual else "provider_global" if variant in ["provider_exact", "null_winner"] else "legacy_normalized_global",
                        variant_key="manual:owned" if manual else "provider:exact" if variant in ["provider_exact", "null_winner"] else "owned:normalized:" + str(i),
                        source_id=None if manual else self.fixture.ids["source"], source_record_id=None if manual else self.fixture.ids["record"])
                    retained = self.fixture._row("football.team_profile_versions", "team_id=%s AND profile_context=%s AND variant_key=%s AND recorded_to_gen IS NULL",
                        (actor, values["profile_context"], values["variant_key"]))
                    if retained:
                        self.fixture._replace("football.team_profile_versions", retained, **values)
                    else:
                        self.fixture._insert("football.team_profile_versions", **values)
            self.fixture.refresh()
            if action != "ambiguous_profile":
                witness["expectedSelections"] = self.profile_selections()
            def restore_profiles():
                with self.fixture._generation("restore_profile_test") as g:
                    self.fixture.data_generation = self.fixture.catalog_generation = g
                    for row in self.fixture.at("football.team_profile_versions", "team_id=%s", (actor,)):
                        self.fixture._replace("football.team_profile_versions", row, is_canonical=False)
            restore = restore_profiles
        elif action == "observed_null_final":
            mid = "m_000003"; match = self.fixture.match_rows[mid]
            with self.fixture._generation("observed_null_final") as g:
                self.fixture.data_generation = self.fixture.catalog_generation = g
                for side in ["home", "away"]:
                    self.fixture._insert("football.match_scores", match_id=match["id"], side=side, goals=None, score_scope="final_without_shootout",
                        score_basis="unknown", match_team_revision_id=self.fixture.sides[mid][side]["revision_id"],
                        source_id=self.fixture.ids["source"], source_record_id=self.fixture.ids["record"])
            self.fixture.expected[mid]["scoreObserved"] = True
            witness["matchId"] = match["id"]
        elif action == "drop_known_kickoff":
            mid = "m_000001"; original = self.fixture.match_rows[mid]
            def change_time(value):
                with self.fixture._generation("fixture_time_change") as g:
                    self.fixture.data_generation = self.fixture.catalog_generation = g
                    row = self.fixture.at("football.matches", "id=%s", (original["id"],))[0]
                    fresh = self.fixture._replace("football.matches", row, kickoff_at=value, kickoff_precision="second" if value else "date", data_revision=row["data_revision"] + 1)
                    alias = self.fixture.at("ingest.public_aliases", "route_kind='match' AND match_id=%s", (row["id"],))[0]
                    self.fixture._replace("ingest.public_aliases", alias, match_revision_id=fresh["revision_id"])
                self.fixture.refresh()
            change_time(None)
            restore = lambda: change_time(original["kickoff_at"])
        elif action == "streamed_scope_over_5000":
            witness = self.fixture.stream_family()
            # Deliberately retain this accepted synthetic correction. Downgrading
            # a present collection to old unavailable metadata is not a restore.
        else:
            raise AssertionError("Unknown concrete fixture mutation: " + action)
        self.owner_epoch()
        try:
            yield witness
        except BaseException:
            raise
        else:
            if restore:
                restore(); self.owner_epoch()

    def native_reject(self, action, states):
        assert action == "incompatible_team_anchor"
        old = self.fixture.sides["m_000001"]["home"]
        try:
            with self.fixture._generation("incompatible_team_anchor"):
                self.fixture._replace("football.match_teams", old, team_id=self.fixture.ids["teams"][4]["id"], data_revision=old["data_revision"] + 1)
                self.db.execute("SET CONSTRAINTS ALL IMMEDIATE")
        except self.psycopg.Error as error:
            assert error.sqlstate in states
        else:
            raise AssertionError("Native incompatible anchor was accepted")
        self.fixture.refresh()

    def correct(self, key):
        if key == "bench_positive_minutes":
            self.fixture.mutate_minutes("positive")
            self.fixture.expected_played[self.bench_pair] = True
        elif key in ["A", "C"]:
            mid = "m_000001" if key == "A" else "m_000005"
            match = self.fixture.match_rows[mid]
            old = self.fixture.at("football.match_scores", "match_id=%s AND side='home' AND score_scope='final_without_shootout'", (match["id"],))[0]
            with self.fixture._generation("correct_" + key) as g:
                self.fixture.data_generation = self.fixture.catalog_generation = g
                self.fixture._replace("football.match_scores", old, goals=old["goals"] + 1, data_revision=old["data_revision"] + 1)
                self.fixture.mark_dirty(key, g)
            self.fixture.expected[mid]["home"] = old["goals"] + 1
        elif key == "shared":
            with self.fixture._generation("shared_profile_correction") as g:
                self.fixture.data_generation = self.fixture.catalog_generation = g
                team = self.fixture.ids["teams"][0]["id"]
                values = dict(team_id=team, display_name="Shared team corrected", observed_at=datetime.now(timezone.utc), is_canonical=True,
                    profile_context="provider_global", variant_key="provider:exact", source_id=self.fixture.ids["source"], source_record_id=self.fixture.ids["record"])
                retained = self.fixture._row("football.team_profile_versions", "team_id=%s AND profile_context='provider_global' AND variant_key='provider:exact' AND recorded_to_gen IS NULL", (team,))
                if retained:
                    self.fixture._replace("football.team_profile_versions", retained, **values)
                else:
                    self.fixture._insert("football.team_profile_versions", **values)
                old = self.fixture.at("football.player_profile_versions", "player_id=%s AND profile_context='provider_global' AND variant_key='provider:exact'", (self.fixture.ids["players"][0]["id"],))[0]
                self.fixture._replace("football.player_profile_versions", old, display_name="Shared striker corrected", external_profile_version_id="owned_shared_v2",
                    profile_content_sha256=hashed("owned_shared_v2"), data_revision=old["data_revision"] + 1)
                self.fixture.mark_dirty("B", g)
            for value in self.fixture.expected.values():
                if value["key"] in ["A", "B"]:
                    value["homeName"] = "Shared team corrected"
        else: raise AssertionError("Unknown fixture correction")
        self.owner_epoch()
        if key != "bench_positive_minutes":
            self.apply_admission()

    def assert_products(self):
        closures = self.independent_closures()
        rows = self.db.execute("""SELECT p.competition_season_id,b.id,b.dependencies_sha256,b.code_commit,b.code_content_sha256,
            d.generation,c.generation FROM analytics.publication_versions p JOIN analytics.aggregation_builds b ON b.id=p.build_id
            JOIN ingest.dataset_snapshots d ON d.id=b.dataset_snapshot_id JOIN ingest.dataset_snapshots c ON c.id=b.catalog_snapshot_id
            WHERE p.published_to_gen IS NULL ORDER BY 1""").fetchall()
        assert len(rows) == len(self.fixture.editions)
        for eid, bid, digest, commit, code, dg, cg in rows:
            assert digest == closures[str(eid)] and code == sha(HELPERS["publish"]) and commit == self.release_doc["codeCommit"]
            effective = self.oracle.closure(eid, dg, cg)
            assert effective["sha256"] == digest
            native_matches = {r["id"]: r for r in self.fixture.at("football.matches", "competition_season_id=%s", (eid,))}
            outputs = self.db.execute("SELECT match_id,match_revision_id,match_date,kickoff_at,status,home_team_id,away_team_id,home_goals,away_goals,score_scope,home_shootout_goals,away_shootout_goals FROM analytics.match_summary WHERE build_id=%s ORDER BY match_id", (bid,)).fetchall()
            assert len(outputs) == len(native_matches)
            for value in outputs:
                source = native_matches[value[0]]
                public = next(mid for mid, row in self.fixture.match_rows.items() if row["id"] == value[0])
                want = self.fixture.expected[public]
                sides = self.fixture.sides[public]
                assert value[1:5] == (source["revision_id"], source["match_date"], source["kickoff_at"], source["status"])
                assert value[5:9] == (sides["home"]["team_id"], sides["away"]["team_id"], want["home"], want["away"])
                assert value[9:] == ("final_without_shootout" if want["scoreObserved"] else None, want["homePenalty"], want["awayPenalty"])
            expected = (len(native_matches), sum(m["status"] == "finished" for m in native_matches.values()),
                len(self.fixture.at("football.competition_teams", "competition_season_id=%s", (eid,))),
                len({r["player_id"] for r in self.fixture.at("football.match_players") if r["match_id"] in native_matches}), None)
            assert self.db.execute("SELECT matches_count,finished_matches_count,teams_count,players_count,goals FROM analytics.competition_summary WHERE build_id=%s", (bid,)).fetchone() == expected

    def export_api(self):
        source = BASE.parent / "product-campaign/publisher_http_server.mjs"
        server = source.read_bytes().replace(b"/orion-pro-publisher-20261105/product-campaign/runs/", b"/orion-pro-publisher-20261105/real-boundary-precode/runtime-runs/")
        assert server != source.read_bytes()
        (self.run / "http-server.mjs").write_bytes(server.replace(b'"../../../../dashboard/node_modules/pg/lib/index.js"',
            json.dumps(str(ROOT / "dashboard/node_modules/pg/lib/index.js")).encode()))
        backend = self.run / "api-runtime/dashboard/backend"
        (backend / "services").mkdir(parents=True, exist_ok=True)
        names = ["orion-pro.js", "postgres.js", "database-connection.js", "metrics.js", "cache-policy.js", "cache.js", "relational-match.js",
                 "relational-support.js", "relational-catalog.js", "cdn.js", "relational-core.js", "partition-wire.js", "catalog-model.json", "support-model.json"]
        for name in names: shutil.copy2(ROOT / "dashboard/backend/services" / name, backend / "services" / name)
        shutil.copy2(ROOT / "dashboard/backend/aws-app.js", backend / "aws-app.js")
        shutil.copy2(ROOT / "dashboard/package.json", backend.parent / "package.json")
        node_modules = backend.parent / "node_modules"
        if not node_modules.exists(): node_modules.symlink_to(ROOT / "dashboard/node_modules", target_is_directory=True)
        graph = "\n".join((backend / "services" / n).read_text() for n in names if n.endswith(".js"))
        assert not any(s in graph for s in ["@aws-sdk/", "./files.js", "./data-store.js", "./pitchapi.js", "./neon.js"])

    def start_api(self, cold=False, poisoned_sources=False):
        if cold: self.stop_api()
        if self.api and self.api.poll() is None: return
        if not (self.run / "api-runtime").exists(): self.export_api()
        env = minimal_env()
        env.update(DATABASE_URL=f"postgresql://statarena_runtime@127.0.0.1:{self.pg.port}/{self.database}", DATABASE_CA_PEM=self.cert.read_text(),
            STATARENA_DATA_PROVIDER="aws", STATARENA_TEST_DATABASE="1", STATARENA_PRO_API="1", DATABASE_POOL_MAX="1", STATARENA_METRICS_SAMPLE_RATE="0",
            ORION_PUBLISHER_TEST_RUN=str(self.run), ORION_PUBLISHER_API_RUNTIME=str(self.run / "api-runtime"))
        if poisoned_sources: env.update(NEON_DATABASE_URL="postgresql://forbidden.invalid/no", PITCHAPI_BASE_URL="https://forbidden.invalid")
        err = (self.run / f"api-{len(self.api_streams)}.stderr.log").open("w")
        self.api_streams.append(err)
        self.api = subprocess.Popen(["bun", "--no-env-file", str(self.run / "http-server.mjs")], cwd=self.run / "api-runtime/dashboard", env=env,
                                    stdout=subprocess.PIPE, stderr=err, text=True, start_new_session=True)
        end = min(self.deadline, time.monotonic() + 10)
        while time.monotonic() < end:
            self.check()
            ready, _, _ = select.select([self.api.stdout], [], [], .1)
            if ready:
                line = self.api.stdout.readline()
                with (self.run / "api-startups.jsonl").open("a") as out: out.write(line)
                try: value = json.loads(line)
                except ValueError: continue
                if value.get("event") == "ready":
                    assert value["identity"] == [{"role": "statarena_runtime", "readonly": "on", "statement_timeout": "8s", "lock_timeout": "1s"}]
                    self.origin = "http://127.0.0.1:" + str(value["port"])
                    return
            assert self.api.poll() is None, "Actual API startup failed"
        raise AssertionError("Actual API startup deadline")

    def stop_api(self):
        if self.api and self.api.poll() is None:
            os.killpg(self.api.pid, signal.SIGTERM)
            try: self.api.wait(timeout=3)
            except subprocess.TimeoutExpired: os.killpg(self.api.pid, signal.SIGKILL); self.api.wait(timeout=2)
        for stream in self.api_streams:
            if not stream.closed: stream.close()

    def http(self, path, method="GET", headers=None):
        self.check(); self.http_serial += 1
        rid = f"h{self.http_serial:03d}"
        opener = build_opener(ProxyHandler({}))
        try: response = opener.open(Request(self.origin + path, method=method, headers={"x-e2e-id": rid, **(headers or {})}), timeout=9)
        except HTTPError as error: response = error
        body = response.read().decode()
        end = min(self.deadline, time.monotonic() + 1)
        trace = None
        while time.monotonic() < end and trace is None:
            file = self.run / "api-requests.jsonl"
            trace = next((json.loads(line) for line in file.read_text().splitlines() if json.loads(line)["id"] == rid), None) if file.exists() else None
            if trace is None: time.sleep(.005)
        assert trace is not None
        row = {"id": rid, "path": path, "method": method, "status": response.status, "body": body,
               "headers": {k.lower(): v for k, v in response.headers.items()}, "sql": trace["sql"]}
        self.requests.append(row)
        return row

    def current_paths(self):
        self.start_api()
        manifest = json.loads(self.http("/api/dashboard/manifest")["body"])
        tokens = {e["season"]: e["representationToken"] for e in manifest["editions"]}
        result = []
        for key, edition in self.fixture.editions.items():
            token = tokens[edition["season_key"]]
            primary = {"A": "m_000001", "B": "m_000004", "C": "m_000005"}[key]
            query = urlencode({"v": token})
            result += ["/api/dashboard/manifest?" + query, "/api/fixtures?" + urlencode({"v": token, "league": "l_000001", "season": edition["season_key"], "limit": 2}),
                       "/api/matches/" + primary + "/summary?" + query, "/api/pitchapi/matches/" + primary + "/shots?" + query]
            if key == "A": result += ["/api/matches/m_000006/summary?" + query, "/api/pitchapi/matches/m_000006/shots?" + query]
        return result

    def assert_metadata_only(self, response):
        assert not any(re.search(r"\bfootball\.(shots|match_heatmaps|match_heatmap_cells|pass_networks)\b|/\*orion:(list|summary|shots)\*/", row.get("sql", ""), re.I) for row in response["sql"])

    def assert_current_http(self):
        for path in self.current_paths():
            row = self.http(path)
            if path.startswith("/api/pitchapi/matches/m_000006/"):
                assert row["status"] == 404 and row["headers"]["cache-control"] == "no-store"
                assert json.loads(row["body"])["error"]["state"] == "unknown"
                self.assert_metadata_only(row)
                continue
            assert row["status"] == 200
            value = json.loads(row["body"])
            if "/summary?" in path:
                match = value["data"]["match"]
                want = self.fixture.expected[match["id"]]
                native = self.fixture.match_rows[match["id"]]
                assert match["date"] == want["date"] and match["status"] == want["status"]
                assert match["timeUtc"] == (native["kickoff_at"].astimezone(timezone.utc).strftime("%H:%M:%S") if native["kickoff_at"] else None)
                for side in ["home", "away"]:
                    assert match[side]["score"] == want[side] and match[side]["scorePenalty"] == want[side + "Penalty"]
                    assert match[side]["name"] == want[side + "Name"]
                assert match["shots"] == match["stats"] == match["leadingPlayers"] == []
                assert not any("football.shots" in q.get("sql", "") for q in row["sql"])
            if "/shots?" in path:
                for period in value["data"]["periods"]:
                    for shot in period["shots"]:
                        assert shot["x"] is shot["y"] is None and shot["coordinate_state"] == "unknown"

    def save_http_baselines(self):
        self.start_api()
        self.old_http = {path: self.http(path) for path in self.current_paths()}

    def assert_old_http_baselines(self):
        volatile = {"date", "server-timing", "connection", "keep-alive"}
        for path, before in self.old_http.items():
            after = self.http(path)
            assert (before["status"], before["body"]) == (after["status"], after["body"])
            assert {k: v for k, v in before["headers"].items() if k not in volatile} == {k: v for k, v in after["headers"].items() if k not in volatile}

    def close(self):
        for child in self.children:
            if child["process"].poll() is None:
                os.killpg(child["process"].pid, signal.SIGKILL); child["process"].wait(timeout=3)
            for stream in child["streams"]:
                if not stream.closed: stream.close()
        self.stop_api()
        if self.db is not None and not self.db.closed:
            self.db.close()
        if self.pg and self.pg.started:
            self.command([PG_BIN / "pg_ctl", "-D", self.pg.data, "-m", "fast", "-w", "stop"], name="postgres-stop", cleanup=True)
            self.pg.started = False
        if self.pg and self.pg.root.exists():
            shutil.rmtree(self.pg.root)
        self.cleanup = {"serverStopped": self.pg is None or not self.pg.started, "apiStopped": self.api is None or self.api.poll() is not None,
                        "workersStopped": all(c["process"].poll() is not None for c in self.children), "ownedDirectoryRemoved": self.pg is None or not self.pg.root.exists()}
