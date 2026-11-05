# Readonly committed-core recovery v2

This is a separate controller, test, pin set and once-only allocation. Every v1
file, release, consumed allocation and failed receipt stays exact. The v1 attempt
proved native P1/identity/core membership and478547independent native31slots with
source=SQL SHA5f9175c1526ad2db4426ebe02d3e412e20999c2bd6486aef5d82d082f34255e0.
It failed its readonly owner guard before67sequence values or fresh core no-op.
It restarted once, decoded1RAM snapshot, wrote no business data, stopped PG and
retained the typed root. These observations are not reset or reclassified.

The narrow v2 change is specified before its new implementation:

* Prove database postgres is owned by orion_pro_owner before the membership test.
* For orion_pro_owner only, require effective memberships exactly
  [pg_database_owner]. Require that predefined role's native OID6171, NOLOGIN,
  nonsuperuser/NOCREATEROLE/NOCREATEDB/NOREPLICATION/NOBYPASSRLS flags.
* Require zero explicit pg_auth_members rows for every actor, including owner.
  This distinguishes the implicit database-owner relationship from a new grant.
* For orion_pro_runtime and orion_pro_ingest, effective memberships remain empty.
  All actors still require zero privileged flags, exact native role/owner/ACL,
  literal loopback/TLS, RO Repeatable Read,8s SQL/1s locks/15s idle.
* Save observed memberships/flags in evidence. A different owner, extra effective
  or explicit membership or privileged flag must refuse; do not add any grant.

Installed PostgreSQL18catalogue definitions support this distinction without a
network or PG connection. information_schema.sql applicable_roles explicitly
UNIONs current database datdba with the pg_database_owner role independently of
pg_auth_members. postgres.bki declares that predefined role6171and its flags.
Their exact paths, snippets and SHA256values are captured in ROLE_OWNER_EVIDENCE.md
and PINS_V2.json. This is preparation evidence, not a live v2 observation.

All remaining v1 PROTOCOL.md outcomes/bounds apply unchanged. The future workflow
must complete independent native94and67sequence values before and after the
separate frozen-candidate core_only=True no-op, with2new RAM GETs and no business
mutation. The first GET from v1 remains separately accounted for. Unexecuted
stages are recorded as such after any unexpected failure. The sole retained root
may be restarted once by this distinct allocation; failure/STOP stops PG and
preserves the corpus. READY remains idle for ROOT's exact RDS transport release.

New artifacts use controller_v2.py, e2e_v2.py, PINS_V2.json, runs-v2 and
core-native-marker-v2.json. No v1 code/marker/result, producer, schema, original
source ledger or transport21+9byte changes. No migration, setval, construction,
spatial replay, raw-body write or corpus deletion. Proposed bounds remain1restart,
2RAM GETs,300s active,3GiB retained allocated disk,64MiB proof,3600s idle.

Suggested commit: `fix: recognize implicit database owner in readonly core recovery`.
