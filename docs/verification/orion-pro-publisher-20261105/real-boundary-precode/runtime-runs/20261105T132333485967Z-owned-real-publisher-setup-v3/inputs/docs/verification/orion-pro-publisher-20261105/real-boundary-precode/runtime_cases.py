"""Executable, pre-implementation real-publication E2E case functions.

These functions exercise actual CLI children, native PostgreSQL and HTTP through
Runtime. They do not import the admission/publisher implementation or compute
expected values with a production planner. No case is considered executed merely
because its function exists.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone


def R00(c):
    for stage in ["admit", "publish"]:
        result = c.help(stage)
        assert result.returncode == 0 and "receipt" in result.stdout and "environment" in result.stdout


def R01(c):
    for stage in ["admit", "publish"]:
        result, receipt = c.invoke(stage, offline=True, tripwire=True,
            env={"PGHOSTADDR": "192.0.2.1", "PGSERVICE": "forbidden", "PGOPTIONS": "-c role=postgres",
                 "DATABASE_URL": "postgresql://forbidden.invalid/forbidden"})
        assert result.returncode == 0 and receipt["status"] == "offline_plan" and receipt["connections"] == 0


def R02(c):
    changes = [lambda x: x.pop("sourcePolicy"), lambda x: x.update(unknownField=True),
               lambda x: x["editions"][0].update(editionId=True),
               lambda x: x["editions"][0].update(editionRevisionId=1.0),
               lambda x: x.update(sourceReconciliationSha256="0" * 64)]
    for patch in changes:
        c.reject("admit", patch=patch, before_driver=True)
    c.reject("admit", raw=b'{"schemaVersion":1,"schemaVersion":1}', before_driver=True)
    c.reject("admit", raw=b'{"schemaVersion":NaN}', before_driver=True)


def R03(c):
    for patch in [lambda x: x.update(fixtureOnly=True),
                  lambda x: x.update(kind="synthetic_declared_business_admission"),
                  lambda x: x.update(sourcePolicy="pilot_priority_v1"),
                  lambda x: x["publisher"].update(commit="local-owned-e2e-v1"),
                  lambda x: x["transport"].update(sourceProducerVersion="unreviewed")]:
        c.reject("publish", patch=patch, before_driver=True)
    # Real endpoint mode is intentionally offered an owned fixture origin. The
    # only acceptable result is a refusal before a connection, never RDS access.
    c.reject("publish", environment="rds", before_driver=True)


def R04(c):
    for key, value in [("PGHOSTADDR", "192.0.2.1"), ("PGHOST", "127.0.0.2"), ("PGSERVICE", "foreign"),
                       ("PGSERVICEFILE", "/forbidden"), ("PGPASSFILE", "/forbidden"),
                       ("PGOPTIONS", "-c statement_timeout=0"), ("PGUSER", "postgres"),
                       ("PGDATABASE", "other"), ("PGPASSWORD", "not-a-credential"),
                       ("PGPORT", "1"), ("PGSSLMODE", "disable"), ("PGSSLROOTCERT", "/forbidden"),
                       ("PGAPPNAME", "foreign"), ("PGTARGETSESSIONATTRS", "read-write"),
                       ("DATABASE_URL", "postgresql://forbidden.invalid/no")]:
        c.reject("admit", env={key: value}, before_driver=True)
    for patch in [lambda x: x.update(hostaddr="192.0.2.1"), lambda x: x.update(hostname="foreign.invalid"),
                  lambda x: x.update(actor="statarena_runtime"), lambda x: x.update(port=1),
                  lambda x: x.update(caSha256="0" * 64)]:
        c.reject("admit", endpoint_patch=patch, before_driver=True)


def R05(c):
    row = c.db.execute("SELECT current_database(),current_user,current_setting('statement_timeout'),current_setting('lock_timeout'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())").fetchone()
    assert row[0] == c.database and row[2:] == ("8s", "1s", True) and c.db.info.server_version == 180006
    journal = c.db.execute("SELECT version,content_sha256 FROM ingest.schema_migrations ORDER BY version").fetchall()
    assert [r[0] for r in journal] == ["012", "013", "014"]
    assert c.catalogue()["counts"] == c.expected_catalogue_counts


def R06(c):
    for field in ["coreCheckpointSha256", "sourceNative31Sha256", "targetNative31ReadbackSha256", "sourceTargetMappingSha256"]:
        c.reject("admit", patch=lambda x, field=field: x["transport"].pop(field), before_driver=True)
    assert c.native31() == c.initial_native31
    assert c.db.execute("SELECT count(*) FROM football.match_heatmaps").fetchone() == (0,)


def R07(c):
    assert c.db.execute("SELECT count(*) FROM analytics.aggregation_builds").fetchone() == (0,)
    assert set(r[0] for r in c.selected("football.matches", ["publication_state"])) == {"draft"}
    c.reject("publish", mode="publish", code="DRAFT_NOT_ADMITTED")
    before = c.state()
    _, result = c.invoke("admit", mode="plan")
    assert result["status"] == "planned" and c.state() == before


def R08(c):
    for patch in [lambda x: x["editions"][0]["members"].pop(),
                  lambda x: x["editions"][0]["members"].append(copy.deepcopy(x["editions"][0]["members"][0])),
                  lambda x: x["editions"][0]["members"][0].update(matchRevisionId=9223372036854775807)]:
        c.reject("admit", patch=patch)
    c.apply_admission()
    assert c.selected_count("football.matches", "publication_state='published'") == len(c.expected_matches)
    assert c.native31() == c.initial_native31


def R09(c):
    rows = c.selected("football.competition_teams", ["competition_season_id", "team_id", "status", "provenance_kind", "source_record_id"])
    assert {(r[0], r[1]) for r in rows} == c.expected_engagements
    assert all(r[2:4] == ("observed", "derived") and r[4] is not None for r in rows)


def R10(c):
    rows = c.selected("football.match_players", ["match_id", "player_id", "played", "participation_evidence"])
    for mid, pid, played, evidence in rows:
        expected = c.expected_played[(mid, pid)]
        assert played is expected and (expected is not True or bool(evidence))
    for kind in ["null", "absent", "string", "boolean", "zero"]:
        with c.fixture_change("minutes_state", kind=kind):
            c.apply_admission()
            row = c.selected_player(c.bench_pair)
            assert row["played"] is None, (kind, row["played"])


def R11(c):
    # The real corpus has source actor IDs whose SQL links are NULL; the fixture
    # carries an analogous declared unresolved actor without inventing a player.
    with c.input_change("unresolved_actor"):
        c.reject("admit", code="ACTOR_UNRESOLVED")
    with c.fixture_change("resolved_shot_without_performance") as witness:
        before = c.native31()
        c.apply_admission()
        player = c.selected_player(witness["pair"])
        assert player["played"] is True and player["provenance_kind"] == "derived"
        assert player["participation_evidence"] and c.native31() == before
        assert c.db.execute("SELECT count(*) FROM football.player_match_stats WHERE match_id=%s AND player_id=%s", witness["pair"]).fetchone() == (0,)


def R12(c):
    rows = c.selected("football.match_teams", ["match_id", "side", "participant_label", "source_record_id"])
    assert all(r[2] == c.expected_labels[(r[0], r[1])] and r[3] is not None for r in rows)
    for issue in ["wrong_team_name_id", "missing_name_locator", "unproved_name_presence"]:
        with c.input_change(issue):
            c.reject("admit")


def R13(c):
    for variant in ["provider_exact", "normalized", "manual", "null_winner"]:
        with c.fixture_change("profile_priority", variant=variant) as witness:
            c.apply_admission()
            plan = c.publish_plan()
            assert plan["profileSelections"] == witness["expectedSelections"]
    with c.fixture_change("ambiguous_profile"):
        c.reject("publish", code="PROFILE_AMBIGUOUS")


def R14(c):
    # Every old anchor remains a retained row; compatibility is membership, not
    # equality with an arbitrary latest revision.
    for raw in c.raw_match_rows:
        current = c.match(raw["id"])
        assert current["id"] == raw["id"] and current["revision_id"] != raw["revision_id"]
        for column in c.immutable_match_values:
            assert current[column] == raw[column], column
        alias = c.match_alias(raw["id"])
        assert alias["match_revision_id"] == current["revision_id"]
    assert c.native31() == c.initial_native31
    c.native_reject("incompatible_team_anchor", {"23503", "23514"})


def R15(c):
    with c.fixture_change("observed_null_final") as witness:
        c.apply_admission()
        plan = c.publish_plan()
        row = next(x for x in plan["matchProducts"] if x["matchId"] == witness["matchId"])
        assert row["scoreScope"] == "final_without_shootout" and row["homeGoals"] is row["awayGoals"] is None
    for issue in ["ignored_available_shootout", "wrong_final_scope", "absent_score_relabelled_zero"]:
        with c.input_change(issue):
            c.reject("admit")


def R16(c):
    for match in c.raw_match_rows:
        current = c.match(match["id"])
        assert current["kickoff_at"] == match["kickoff_at"] and current["match_date"] == match["match_date"]
    with c.fixture_change("drop_known_kickoff"):
        c.reject("admit", code="FIELD_STATE_MISMATCH")
    with c.input_change("infer_midnight_for_unknown"):
        c.reject("admit", code="FIELD_STATE_MISMATCH")


def R17(c):
    for issue in ["coverage_same_count_wrong_ids", "coverage_wrong_variant", "coverage_wrong_revision", "coverage_stale_key", "shot_wrong_period", "shot_wrong_actor"]:
        with c.input_change(issue):
            c.reject("admit", code="COVERAGE_INVALID")
    assert c.coverage_sets() == c.expected_coverage_sets


def R18(c):
    # Numeric raw x/y without proven units/frame are deliberately unqualified.
    # They must never become metre coordinates or a fabricated acting_ltr frame.
    for row in c.selected("football.shots", ["x_m", "y_m", "coordinate_frame"]):
        assert row == (None, None, None)
    with c.input_change("infer_metres_or_acting_ltr"):
        c.reject("admit", code="COORDINATES_UNQUALIFIED")
    with c.input_change("unmapped_available_field_claimed_observed_null"):
        c.reject("admit", code="FIELD_STATE_MISMATCH")


def R19(c):
    assert c.source_identity_facts() == c.initial_source_identity_facts
    assert c.native31() == c.initial_native31
    rows = c.selected("football.competition_teams", ["transform_version", "transform_code_sha256", "provenance_kind"])
    assert all(r == (c.admission_transform, c.admission_code_sha, "derived") for r in rows)
    with c.input_change("derived_input_closure_changed"):
        c.reject("publish", code="ADMISSION_STALE")


def R20(c):
    with c.fixture_change("streamed_scope_over_5000") as witness:
        c.apply_admission()
        plan = c.publish_plan()
        assert witness["selectedRows"] > 5000
        assert plan["selectedRows"] >= witness["selectedRows"] and plan["dependenciesSha256"] == c.independent_closures()
        assert plan["maxBufferedRows"] <= 1000 and plan["omittedRows"] == 0


def R21(c):
    c.apply_admission()
    result = c.publish()
    assert result["status"] == "published"
    c.assert_products()
    assert c.db.execute("SELECT count(*) FROM analytics.aggregation_builds WHERE status<>'ready'").fetchone() == (0,)
    c.save_http_baselines()


def R22(c):
    c.start_api(cold=True)
    for path in c.current_paths():
        head = c.http(path, "HEAD")
        assert head["status"] in {200, 404} and not head["body"]
        c.assert_metadata_only(head)
        if head["status"] == 200:
            conditional = c.http(path, headers={"if-none-match": head["headers"]["etag"]})
            assert conditional["status"] == 304 and not conditional["body"]
            c.assert_metadata_only(conditional)
        else:
            assert head["headers"]["cache-control"] == "no-store" and "etag" not in head["headers"]
    c.assert_current_http()


def R23(c):
    c.correct("A")
    before = c.state()
    killed = c.start("publish", barrier="before_ready_commit")
    c.phase(killed, "before_ready_commit")
    c.kill(killed)
    assert c.state() == before
    orphan = c.start("publish", barrier="after_ready_commit")
    event = c.phase(orphan, "after_ready_commit")
    ids = event["buildIds"]
    c.kill(orphan)
    a, b = c.start("publish", barrier="after_plan"), c.start("publish", barrier="after_plan")
    c.phase(a, "after_plan"); c.phase(b, "after_plan")
    c.release(a); c.release(b)
    c.finish(a); c.finish(b)
    assert set(ids) <= set(c.ready_build_ids())
    c.correct("shared")
    previous = c.active_builds()
    child = c.start("publish", barrier="after_first_pointer_write")
    c.phase(child, "after_first_pointer_write")
    assert c.active_builds() == previous
    c.kill(child)
    assert c.active_builds() == previous
    c.publish()
    c.assert_products()


def R24(c):
    c.correct("C")
    previous = c.active_builds()
    child = c.start("publish", barrier="before_activation_recheck")
    event = c.phase(child, "before_activation_recheck")
    assert event["globalGenerationLockHeld"] is False
    count = c.db.execute("SELECT count(*) FROM pg_locks WHERE pid=%s AND locktype='advisory' AND classid=20261104::oid AND objid=1::oid AND objsubid=2 AND granted", (event["backendPid"],)).fetchone()[0]
    assert count == 0
    c.correct("C")
    watermark = c.dirty()
    c.release(child)
    result = c.finish(child, rejected=True)
    assert result["status"] == "retry" and result["error"]["code"] == "STALE_PLAN"
    assert c.active_builds() == previous and c.dirty() == watermark
    c.publish()


def R25(c):
    for _ in range(2):
        before, trace_offset = c.state(), c.trace_offset()
        result = c.publish()
        assert result["status"] == "noop" and c.state() == before
        assert not any("begin_generation" in row["sql"] or "nextval" in row["sql"] for row in c.trace_since(trace_offset))
    c.assert_old_http_baselines()


def R26(c):
    c.correct("bench_positive_minutes")
    _, result = c.invoke("admit", mode="apply", fault="after_commit_ack")
    assert result["status"] == "retry" and result["error"]["code"] == "COMMIT_ACK_UNKNOWN"
    assert result["outcome"] == "acknowledgment_unknown" and result.get("rolledBack") is not True
    c.refresh_input()
    before = c.state()
    c.apply_admission()
    assert c.state() == before
    _, result = c.invoke("publish", mode="publish", fault="after_commit_ack")
    assert result["status"] == "retry" and result["error"]["code"] == "COMMIT_ACK_UNKNOWN"
    c.refresh_input()
    before = c.state()
    assert c.publish()["status"] == "noop" and c.state() == before


def R27(c):
    for actor, commands in [("statarena_ingest", ["DELETE FROM ingest.dirty_editions WHERE false", "SELECT ingest.validate_aggregation_build(-1)", "SELECT nextval('ingest.commit_generation_seq')"]),
                            ("statarena_runtime", ["UPDATE football.players SET display_name='forbidden' WHERE false"])]:
        with c.connect(actor) as conn:
            conn.execute("SET default_transaction_read_only=off")
            for command in commands:
                try:
                    conn.execute(command)
                except c.psycopg.Error as error:
                    assert error.sqlstate == "42501"
                else:
                    raise AssertionError("Unexpected existing actor privilege")


def R28(c):
    for issue in ["release_absent", "release_expired", "release_reused", "release_wrong_code", "release_wrong_target_readback"]:
        c.reject("publish", release_issue=issue, before_driver=True)


def R29(c):
    c.start_api(cold=True, poisoned_sources=True)
    c.assert_current_http()
    assert c.source_accesses() == []


def R30(c):
    assert c.source_accesses() == [] and c.ram_gets == 0 and c.cloud_calls == 0
    assert c.input_hashes_unchanged()
    c.close()
    assert c.cleanup["serverStopped"] and c.cleanup["apiStopped"] and c.cleanup["workersStopped"]
    assert c.cleanup["ownedDirectoryRemoved"]


CASES = [R00, R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15,
         R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30]
