# Installed PostgreSQL evidence for the owner guard

No PG start, connection, cloud request or RAM GET was performed for this check.

In the bundled PostgreSQL18distribution:

* `/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/share/postgresql/information_schema.sql`,
  lines243-257, defines applicable_roles with a UNION of pg_auth_members and
  `SELECT datdba, pg_authid.oid, false FROM pg_database, pg_authid WHERE datname = current_database() AND rolname = 'pg_database_owner'`.
  The installed comment explicitly distinguishes this from possible explicit
  membership. Therefore an effective owner membership need not be a grant row.
* The same distribution's postgres.bki line11317 declares
  `insert ( 6171 pg_database_owner f t f f f f f -1 _null_ _null_ )`.
  The preceding pg_authid column definitions identify the flags: nonsuperuser,
  inherited role, NOCREATEROLE/NOCREATEDB/NOLOGIN/NOREPLICATION/NOBYPASSRLS.

The v2 guard checks the actual live database owner before accepting exactly this
one implicit membership, then separately requires zero explicit grants. Runtime
and ingest retain their empty-membership requirement. The exact installed file
hashes are in PINS_V2.json and are checked before any future restart.

Suggested commit: `docs: document native implicit database owner membership`.
