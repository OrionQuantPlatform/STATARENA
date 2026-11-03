-- Additive read models; apply before activating the P1 reader/writer rollout.
CREATE TABLE IF NOT EXISTS statarena.fixture_generation (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), generation bigint NOT NULL DEFAULT 1
);
INSERT INTO statarena.fixture_generation(singleton) VALUES(true) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS statarena.match_summaries (
 match_id text PRIMARY KEY REFERENCES statarena.fixtures(id) ON DELETE CASCADE,
 body bytea NOT NULL, sha256 bytea NOT NULL CHECK(octet_length(sha256)=32),
 size integer NOT NULL CHECK(size>=0 AND size<=262144), source_digest text NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS statarena.dirty_match_summaries (
 match_id text PRIMARY KEY, changed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE OR REPLACE FUNCTION statarena.mark_match_summary_dirty() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE identity text;
BEGIN
 IF TG_TABLE_NAME='fixtures' THEN identity := COALESCE(NEW.id,OLD.id);
 ELSIF TG_TABLE_NAME='observations' THEN identity := COALESCE(NEW.id,OLD.id);
 ELSE identity := split_part(COALESCE(NEW.endpoint,OLD.endpoint),'/',3);
 END IF;
 IF identity ~ '^m_[A-Za-z0-9]{6}$' THEN
  INSERT INTO statarena.dirty_match_summaries(match_id) VALUES(identity)
  ON CONFLICT(match_id) DO UPDATE SET changed_at=clock_timestamp();
  INSERT INTO statarena.dirty_partitions(season,league_id)
  SELECT CASE WHEN position('/' in season)>0 THEN season ELSE season||'/'||(season::int+1)::text END,league_id
  FROM statarena.fixtures WHERE id=identity AND season ~ '^\d{4}(/\d{4})?$'
  ON CONFLICT(season,league_id) DO UPDATE SET changed_at=clock_timestamp();
 END IF;
 RETURN NULL;
END $$;
CREATE OR REPLACE TRIGGER fixtures_summary_dirty AFTER INSERT OR UPDATE OR DELETE ON statarena.fixtures FOR EACH ROW EXECUTE FUNCTION statarena.mark_match_summary_dirty();
CREATE OR REPLACE TRIGGER resources_summary_dirty AFTER INSERT OR UPDATE OR DELETE ON statarena.resources FOR EACH ROW EXECUTE FUNCTION statarena.mark_match_summary_dirty();
CREATE OR REPLACE TRIGGER observations_summary_dirty AFTER INSERT OR UPDATE OR DELETE ON statarena.observations FOR EACH ROW EXECUTE FUNCTION statarena.mark_match_summary_dirty();
CREATE OR REPLACE FUNCTION statarena.advance_fixture_generation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='TRUNCATE' THEN UPDATE statarena.fixture_generation SET generation=generation+1;
 ELSIF EXISTS(SELECT 1 FROM changed_rows) THEN UPDATE statarena.fixture_generation SET generation=generation+1;
 END IF; RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS fixtures_generation ON statarena.fixtures;
CREATE OR REPLACE TRIGGER fixtures_generation_insert AFTER INSERT ON statarena.fixtures REFERENCING NEW TABLE AS changed_rows FOR EACH STATEMENT EXECUTE FUNCTION statarena.advance_fixture_generation();
CREATE OR REPLACE TRIGGER fixtures_generation_update AFTER UPDATE ON statarena.fixtures REFERENCING NEW TABLE AS changed_rows FOR EACH STATEMENT EXECUTE FUNCTION statarena.advance_fixture_generation();
CREATE OR REPLACE TRIGGER fixtures_generation_delete AFTER DELETE ON statarena.fixtures REFERENCING OLD TABLE AS changed_rows FOR EACH STATEMENT EXECUTE FUNCTION statarena.advance_fixture_generation();
CREATE OR REPLACE TRIGGER fixtures_generation_truncate AFTER TRUNCATE ON statarena.fixtures FOR EACH STATEMENT EXECUTE FUNCTION statarena.advance_fixture_generation();
CREATE OR REPLACE FUNCTION statarena.mark_shard_summaries_dirty() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO statarena.dirty_match_summaries(match_id)
 SELECT id FROM statarena.observations WHERE shard=NEW.id
 ON CONFLICT(match_id) DO UPDATE SET changed_at=clock_timestamp();
 INSERT INTO statarena.dirty_partitions(season,league_id)
 SELECT DISTINCT CASE WHEN position('/' in f.season)>0 THEN f.season ELSE f.season||'/'||(f.season::int+1)::text END,f.league_id
 FROM statarena.fixtures f JOIN statarena.observations o ON o.id=f.id WHERE o.shard=NEW.id AND f.season ~ '^\d{4}(/\d{4})?$'
 ON CONFLICT(season,league_id) DO UPDATE SET changed_at=clock_timestamp();
 RETURN NULL;
END $$;
CREATE OR REPLACE TRIGGER shards_summary_dirty AFTER UPDATE ON statarena.shards FOR EACH ROW WHEN(OLD.ref IS DISTINCT FROM NEW.ref) EXECUTE FUNCTION statarena.mark_shard_summaries_dirty();

-- Preserve existing reader/writer role permissions, without a PUBLIC grant.
DO $$ DECLARE entry record; BEGIN
 FOR entry IN SELECT a.grantee,a.privilege_type FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL aclexplode(c.relacl) a WHERE n.nspname='statarena' AND c.relname='fixtures' AND a.grantee<>0 LOOP
  EXECUTE format('GRANT %s ON statarena.fixture_generation,statarena.match_summaries,statarena.dirty_match_summaries TO %I',entry.privilege_type,pg_get_userbyid(entry.grantee));
 END LOOP;
END $$;
