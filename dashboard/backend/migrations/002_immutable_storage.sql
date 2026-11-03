-- Reader-first migration. NULL retains the legacy data/<path> lookup.
ALTER TABLE statarena.objects ADD COLUMN IF NOT EXISTS storage_key text;

-- Physical uploads are reserved/accounted independently of publication commits.
-- A reserved entry may overcount a failed upload until a verified inventory reconciles it.
CREATE TABLE IF NOT EXISTS statarena.object_storage (
 storage_key text PRIMARY KEY,
 sha256 bytea NOT NULL CHECK(octet_length(sha256)=32),
 size bigint NOT NULL CHECK(size>=0),
 etag text NOT NULL,
 state text NOT NULL CHECK(state IN ('reserved','verified')),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);

-- Preserve explicit catalog-role capabilities without exposing the ledger to PUBLIC.
DO $$
DECLARE permission record;
BEGIN
 FOR permission IN
  SELECT r.rolname, a.privilege_type
  FROM pg_class c
  CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a
  JOIN pg_roles r ON r.oid=a.grantee
  WHERE c.oid='statarena.objects'::regclass AND a.grantee<>0
    AND a.privilege_type IN ('SELECT','INSERT','UPDATE')
 LOOP
  EXECUTE format('GRANT %s ON TABLE statarena.object_storage TO %I', permission.privilege_type, permission.rolname);
 END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION statarena.reset_legacy_storage_key()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.sha256 IS DISTINCT FROM OLD.sha256
    AND NEW.storage_key IS NOT DISTINCT FROM OLD.storage_key THEN
  NEW.storage_key := NULL;
 END IF;
 RETURN NEW;
END;
$$;
CREATE OR REPLACE TRIGGER objects_legacy_storage_key
BEFORE UPDATE ON statarena.objects
FOR EACH ROW EXECUTE FUNCTION statarena.reset_legacy_storage_key();
