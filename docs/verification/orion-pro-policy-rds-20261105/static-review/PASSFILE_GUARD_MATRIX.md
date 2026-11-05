# Proposed new private passfile guard — before implementation

Planning only. No auth guard/test implementation, file-based connection, SSM, DNS, driver or PG call is authorized by this review. Current adapter332d963… rejects every PG* variable, including PGPASSFILE, and does not consume ORION_RDS_PASSFILE. Actual remote authentication is unqualified. Do not edit ~/.pgpass or add a fallback.

ROOT proposes `ORION_RDS_PASSFILE` containing only an absolute path to a privately provisioned temporary passfile. The coordinator ROOT is not Unix UID0: the expected file/parent UID is the current process's authorized OS UID. A new pure `validated_rds_passfile()` should check metadata before any DNS/driver operation:

1. Require the dedicated environment value to be a nonempty absolute path, not a DSN, credential or CLI secret.
2. lstat the leaf without first resolving it through a symlink. Require regular file, no symlink, exact UID and0600.
3. lstat its direct private parent. Require directory, no symlink, same UID and0700. Common system ancestors such as macOS /tmp→/private/tmp are not the private parent; the caller-created direct parent must itself be private.
4. Return the exact validated absolute path for the explicit libpq `passfile=` keyword. Do not read/parse/print/hash the credential body. Reject inherited PG* options/services/routing as before; ORION_RDS_PASSFILE is not an exemption for PGPASSFILE.
5. Keep host/port/db/admin/engine/CA/startupRO/RR8s/1s fixed. Missing/invalid auth is a generic AUTH refusal before DNS/driver; there is no SSM/default-home authentication fallback. ROOT owns provisioning and cleanup of the temporary file.

Proposed order: immutable inputs/checkpoint/release → PG* refusal → dedicated passfile metadata guard → one-shot ledger claim → fixed endpoint DNS → driver with explicit passfile. Rejecting local configuration before a network attempt must not be described as a consumed source read. No retry is implicitly authorized. Root can choose the exact preconnect-ledger policy in the later release; no ledger is created now.

## Failure cases to write into E2E before the NEW guard exists

The isolated scope is necessary because this guard must refuse bad metadata before forbidden remote operations. Exercise real temporary files/permissions/symlinks, with driver/DNS tripwires and no SQL mocks. First retain an actual missing-new-guard RED without PG; then integrate the same subcases into the single complete owned/TLS campaign, under the existing offline/remote-boundary workflow if ROOT retains20top-level cases. No isolated tests are added after guard implementation.

| Case | Real fixture / expected result |
|---|---|
|NEW guard absent|Real pre-code failure,0PG/DNS/driver; other guard cases unverified.|
|Variable missing / empty|AUTH refusal, no body access or network.|
|Relative path / DSN-shaped value|AUTH refusal before filesystem credential read or network.|
|Missing absolute file|Generic AUTH refusal.|
|Directory / FIFO / socket leaf|Refuse as nonregular without opening/blocking.|
|Leaf symlink / broken symlink|Refuse using lstat; never follow it.|
|Leaf0644/0400/0000/0700|Refuse;0600 is exact.|
|Direct parent0755/0770/0710|Refuse;0700 is exact.|
|Direct parent symlink|Refuse even if its target is private.|
|Wrong owner UID|Use an actually differently owned accessible file where the OS permits; refuse. If permissions prevent constructing a sole-UID counterexample, report that branch not isolated. Do not fake metadata or claim an /etc file's multiple-invalid-properties refusal isolates UID.|
|Valid regular0600/current-UID leaf in private0700/current-UID parent|Return the exact absolute path; no body read. File content is explicitly synthetic and not an actual password.|
|Valid auth plus PGHOSTADDR/PGOPTIONS/PGSERVICE/PGPASSFILE|ROUTE refusal still precedes DNS/driver.|
|Explicit keyword binding|A driver tripwire inspects keyword names/path only: passfile is explicit; no password/DSN secret argument, host/port/db/user/CA/settings remain fixed. No actual external connection.|
|Invalid auth output/proof|Only generic code/type and safe permission observations; no body/secret path value echoed in errors or logs.|

These metadata tests do not prove successful RDS password authentication, parser correctness of the secret file, role existence or permissions. An eventual ROOT-only RO release must separately qualify those against the actual endpoint while retaining the fixed budget. The local PG fixture continues to use its owned trust/TLS configuration and is not a substitute for that remote evidence.

Suggested commit: `test: audit owned RDS policy fixtures before continuation`.
