# New private passfile guard — test before code

ROOT authorizes source-free preparation only. This new guard is absent in adapter332d963. Write these real-file cases first, retain actual missing-guard RED without PG, then implement the guard and keep the identical cases for the later complete owned/TLS E2E. No PG/cloud/DNS/SSM/source/RAM access, actual release/ledger creation or user's home password-file change.

New APIs: `validated_rds_passfile(environ=None)` and private `_rds_connection_kwargs(passfile,address)`. The former rejects all PG* options, requires ORION_RDS_PASSFILE as an absolute raw path, lstat-checks regular/no-symlink/current-UID/exact0600 leaf and raw no-symlink/current-UID/exact0700 direct parent before returning the exact path. It never reads a body or falls back to HOME. The latter returns the fixed RDS/TLS/RO8s1s connection keywords with explicit passfile, not password. The actual remote caller must invoke validation before ledger claim/DNS/driver. No remote apply switch.

Cases: missing/empty, relative/DSN, missing leaf, directory/FIFO/socket, leaf/broken symlink, wrong file modes, wrong parent modes, parent symlink, actual wrongUID when OS permits, valid private file/no body access, every PG* still refused, explicit fixed kwargs, generic error redaction, and no HOME fallback. Real synthetic files only; driver/DNS/body-read tripwires; no SQL mocks. WrongUID is explicitly unisolated when the OS refuses a sole-UID fixture, never fabricated or counted passed. Dummy file content is synthetic and removed; no secret file is read or archived.

The isolated scope is necessary to prove metadata refusal before forbidden network operations. It covers only NEW absent guard/kwargs helpers and is written before them. These same subcases are imported by the full E2E. It does not prove actual RDS password authentication or private-file parser correctness. Full local20cases still await ROOT's distinct release/ledger and compact slot.

Suggested commit: `fix: qualify exact RDS policy metadata and private authentication`.
