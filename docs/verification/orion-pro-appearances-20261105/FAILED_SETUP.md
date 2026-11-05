# Preserved pre-code setup attempt

Suggested commit: `test: qualify the typed appearance fixture before readers`.

Run20261105T134419277342Z-actual-node24-precode-red stopped before any case or
HTTP request: the harness set PGSERVICE to an empty string while disabling private
service/password files. libpq treated this as a named empty service and refused
the connection (`definition of service "" not found`). This is a harness setup
failure, not the planned missing-reader RED. All22cases remain unverified.
The owned PostgreSQL was stopped and removed; no application server was started.

The original result's SQL count1 precharged a future Node startup identity query
that did not execute. Actual database SQL was0 (adminSQL empty, no server/log).
The harness now increments that query only after actual Node server readiness.
It deletes the PGSERVICE key, disables private pass/service files, supplies an
empty local password and keeps all connection parameters explicitly loopback.
No credential value is read or copied. No fixture, product or functional
expectation changed. The failed input archive and original ledger are retained.

Run20261105T134734684133Z-actual-node24-precode-service-v2 passed connection,
schema/bootstrap, read-only Node24 startup and the original213-row fixture, then
stopped at A01: the new synthetic metric definition omitted its required
definition text. All previous source pins were unchanged,347externalSQL calls,
0HTTP, PostgreSQL/Node/admin stopped and owned directory removed. No reader
behavior was reached. The fixture now supplies that descriptive text; schema and
functional expectations stay exact. The harness also replaces /dev/null with
owned empty0600pass/service files to avoid libpq's non-regular-file warning.

Run20261105T135214002381Z-actual-node24-precode-definition-v3 stopped in A01
after561externalSQL/0HTTP: the new team-stat fixture attempted a clearances
column that the approved team_match_stats table does not define. The fixture
insertion guard rejected it before SQL; no schema change was made. This optional
unrepresented projection is now omitted (not replaced with zero); it is outside
the ten existing club-style indicators being exercised. All existing functional
expectations stay exact. A static audit now verifies every literal fixture
insert/replace keyword against the unchanged model before the next attempt.

Run20261105T135725300458Z-actual-node24-precode-model-v4 stopped in A01 after
564externalSQL/0HTTP: the fixture supplied raw pitch coordinates without a declared
coordinate frame, correctly rejected by football_match_players_coords_frame_ck.
The synthetic source now explicitly declares fixture_raw_untransformed; no unit,
rotation or sporting coordinate convention is inferred. It is part of the saved
source descriptor and expected output. No reader/model or other expectation
changed. The owned PostgreSQL/Node/admin were closed and removed as before.
