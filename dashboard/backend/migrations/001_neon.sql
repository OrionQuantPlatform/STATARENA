-- Additive migration: original sources stay in private Neon Object Storage.
CREATE SCHEMA IF NOT EXISTS statarena;
CREATE TABLE IF NOT EXISTS statarena.objects (
 path text PRIMARY KEY, size bigint NOT NULL CHECK(size>=0), sha256 bytea NOT NULL,
 etag text NOT NULL, body bytea, content_type text NOT NULL DEFAULT 'application/json',
 updated_at timestamptz NOT NULL DEFAULT now(), storage_key text
);
-- Keep fresh installs aligned with additive migration 002_immutable_storage.sql.
ALTER TABLE statarena.objects ADD COLUMN IF NOT EXISTS storage_key text;
CREATE TABLE IF NOT EXISTS statarena.object_storage (
 storage_key text PRIMARY KEY,
 sha256 bytea NOT NULL CHECK(octet_length(sha256)=32),
 size bigint NOT NULL CHECK(size>=0),
 etag text NOT NULL,
 state text NOT NULL CHECK(state IN ('reserved','verified')),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
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
CREATE TABLE IF NOT EXISTS statarena.resources (
 endpoint text NOT NULL, params text NOT NULL DEFAULT '{}', status smallint NOT NULL,
 ref jsonb, error jsonb, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(endpoint,params)
);
CREATE TABLE IF NOT EXISTS statarena.shards (id text PRIMARY KEY, ref jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS statarena.observations (id text PRIMARY KEY, shard text NOT NULL REFERENCES statarena.shards(id), ordinal integer NOT NULL);
CREATE TABLE IF NOT EXISTS statarena.fixtures (
 id text PRIMARY KEY, league_id text NOT NULL, season text NOT NULL, day date,
 status text, body jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS fixtures_day ON statarena.fixtures(day,status);
CREATE INDEX IF NOT EXISTS fixtures_league_season ON statarena.fixtures(league_id,season,status);
CREATE TABLE IF NOT EXISTS statarena.jobs (
 endpoint text NOT NULL, params text NOT NULL DEFAULT '{}', priority smallint NOT NULL DEFAULT 3,
 state text NOT NULL DEFAULT 'pending' CHECK(state IN('pending','running','done','unavailable')),
 attempts integer NOT NULL DEFAULT 0, available_at timestamptz NOT NULL DEFAULT now(),
 lease_until timestamptz, last_status smallint, last_error text, PRIMARY KEY(endpoint,params)
);
CREATE INDEX IF NOT EXISTS jobs_pending ON statarena.jobs(priority,available_at) WHERE state='pending';
CREATE INDEX IF NOT EXISTS jobs_leases ON statarena.jobs(lease_until) WHERE state='running';
CREATE TABLE IF NOT EXISTS statarena.state (name text PRIMARY KEY, value jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS statarena.projections (name text NOT NULL, params text NOT NULL DEFAULT '{}', body jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(name,params));
CREATE TABLE IF NOT EXISTS statarena.assets (url text PRIMARY KEY, path text NOT NULL REFERENCES statarena.objects(path), content_type text NOT NULL);
CREATE TABLE IF NOT EXISTS statarena.dirty_partitions (season text NOT NULL, league_id text NOT NULL, changed_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(season,league_id));
INSERT INTO statarena.state(name,value) VALUES('revision','1'::jsonb) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS statarena.asset_jobs(url text PRIMARY KEY,attempts int NOT NULL DEFAULT 0,next_attempt timestamptz NOT NULL DEFAULT now(),error text);
CREATE TABLE IF NOT EXISTS statarena.ingest_failures(endpoint text NOT NULL,params text NOT NULL,status smallint NOT NULL,error jsonb,updated_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(endpoint,params));
