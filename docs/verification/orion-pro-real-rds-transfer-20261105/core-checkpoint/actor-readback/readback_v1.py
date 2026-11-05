#!/usr/bin/env python3
"""Once-only ROOT-scoped four-SELECT actor metadata readback; no source bodies."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import sys,time

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]
SOURCE=ROOT/'docs/verification/orion-pro-real-rds-transfer-20261105/core-checkpoint/runs-v2/20261105T115732447984Z'
DOCUMENT='computed/dashboard/2025-2026/l_3FJFUl-1f2cbed49d570024ea3a0ee7.json.gz'
SHA='08ca2af5bbc78703da76839a7d332a7a40f4dd18486972b363af49bd17ffeaa6'
WITNESSES=[['m_0Dz3Fs','p_4D4L8O','t_38NVJO','s_2T49C6','/tables/shots/rows/531','3ba4b34e9037956d5443efbf7ce9b72d7bca02d6bc088e0d6f4107b95557ebcc'],
 ['m_1GY5OE','p_2mYiIC','t_4BCeSu','s_0KideU','/tables/shots/rows/4207','f1b42942439701874ac922eafad46779cb187412028b30a3439ea8573fe06e12'],
 ['m_1GY5OE','p_2mYiIC','t_4BCeSu','s_32KbQY','/tables/shots/rows/4208','de2e055c638ca4c4f7cec4c1afa56ca22e1bba14b2c6ff8d70978df7d7a212ba'],
 ['m_2c4ZLn','p_2mYiIC','t_0xMlRV','s_4RmCm9','/tables/shots/rows/4832','a5da8b40c13536a1d9429f7a80aa4ea20df963f02bcb5d57aa4bbdc073334c3b']]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,default=str)+'\n')
def envelope(sql):return "WITH raw AS MATERIALIZED ("+sql+"),encoded AS MATERIALIZED (SELECT row_to_json(raw)::text v,row_number() OVER() ordinal FROM raw),measured AS (SELECT count(*) n,coalesce(sum(octet_length(v)),0)+greatest(count(*)-1,0)+2 bytes FROM encoded) SELECT CASE WHEN n<=%s AND bytes<=%s THEN (SELECT '['||coalesce(string_agg(v,',' ORDER BY ordinal),'')||']' FROM encoded) END,n,bytes FROM measured"

def main():
    assert not any(k.startswith('PG') for k in os.environ)
    allocation=BASE/'actor-readback-v1.consumed.json';assert not allocation.exists(),'ROOT allocation already consumed'
    run=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    save(allocation,{'run':str(run),'rootScope':'4SELECT/32KiB/source runtime RO only','executions':1})
    report={'kind':'four_shot_actor_global_core_readback_v1','command':[sys.executable,str(Path(__file__))],
        'expected':str(BASE/'PROTOCOL.md'),'witnesses':WITNESSES,'sourceDocument':DOCUMENT,'sourceDocumentSha256':SHA,
        'selects':0,'decodedBytes':0,'queries':[],'sourceRamReads':0,'remoteCalls':0,'businessWrites':0,'fullAcceptance':False}
    marker=json.loads((SOURCE/'checkpoint.json').read_text())['marker'];sys.path.insert(0,'/tmp/statarena-publication-test-python')
    import psycopg
    c=None;started=time.monotonic()
    try:
        c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=55467,dbname='postgres',user='orion_pro_runtime',password='',passfile='/dev/null',
            sslmode='verify-full',sslrootcert=marker['certificatePath'],autocommit=True,connect_timeout=7,
            options='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c timezone=UTC -c search_path=pg_catalog')
        def query(name,sql,params,maximum):
            assert report['selects']<4;report['selects']+=1;tick=time.monotonic()
            payload,count,size=c.execute(envelope(sql),(*params,maximum,8000)).fetchone()
            used=(len(payload.encode()) if payload is not None else 1)+len(str(count))+len(str(size))+32
            report['decodedBytes']+=used;entry={'name':name,'sql':envelope(sql),'params':[*params,maximum,8000],'rowCount':count,'serverBytes':size,'decodedBytes':used,'elapsedMs':round((time.monotonic()-tick)*1000,3)};report['queries'].append(entry)
            assert payload is not None and used<=8192 and report['decodedBytes']<=32768,'Metadata envelope exceeded'
            entry['rows']=json.loads(payload);save(run/'progress.json',report);return entry['rows']
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        identity=query('identity',"SELECT current_database() db,current_user actor,session_user session_actor,current_setting('server_version_num') version,current_setting('transaction_read_only') ro,current_setting('transaction_isolation') isolation,current_setting('statement_timeout') statement,current_setting('lock_timeout') lock,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) tls,pg_postmaster_start_time()::text started",(),1)[0]
        assert [identity[k] for k in ['db','actor','session_actor','version','ro','isolation','statement','lock','tls']]==['postgres','orion_pro_runtime','orion_pro_runtime','180006','on','repeatable read','8s','1s',True]
        assert datetime.fromisoformat(identity['started'])==datetime.fromisoformat(marker['postmasterStartedAt'])
        actors=query('global_player_profile_identity',"""WITH wanted(actor) AS (VALUES('p_4D4L8O'),('p_2mYiIC'))
SELECT w.actor,a.player_id,p.id IS NOT NULL player_exists,
 (SELECT coalesce(json_agg(row_to_json(x)),'[]'::json) FROM (SELECT v.id profile_id,v.player_id,v.external_profile_version_id,v.profile_context,v.recorded_from_gen,r.locator,d.legacy_object_path,d.content_sha256,
   (SELECT coalesce(json_agg(z.public_key ORDER BY z.public_key),'[]'::json) FROM ingest.public_aliases_current z WHERE z.route_kind='profile' AND z.profile_version_id=v.id) profile_public_keys
   FROM football.player_profile_versions v LEFT JOIN ingest.source_records r ON r.id=v.source_record_id LEFT JOIN ingest.source_documents d ON d.id=r.document_id
   WHERE v.player_id=p.id ORDER BY v.id LIMIT 8) x) profiles,
 (SELECT coalesce(json_agg(row_to_json(x)),'[]'::json) FROM (SELECT d.legacy_object_path,d.content_sha256,count(*) rows,min(r.locator) minimum_locator
   FROM football.player_match_stats s JOIN ingest.source_records r ON r.id=s.source_record_id JOIN ingest.source_documents d ON d.id=r.document_id
   WHERE s.player_id=p.id GROUP BY d.legacy_object_path,d.content_sha256 ORDER BY d.legacy_object_path) x) performance_source_documents
FROM wanted w LEFT JOIN ingest.public_aliases_current a ON a.route_kind='player' AND a.public_key=w.actor LEFT JOIN football.players p ON p.id=a.player_id ORDER BY w.actor""",(),2)
        wanted_sql="WITH wanted(match_key,actor,team_key,shot_key,locator) AS (VALUES "+','.join('(%s,%s,%s,%s,%s)' for _ in WITNESSES)+') '
        wanted_params=tuple(v for row in WITNESSES for v in row[:5])
        cohorts=query('exact_requested_participant_cohorts',wanted_sql+"""SELECT w.*,ma.match_id,pa.player_id,ta.team_id,
 (SELECT coalesce(json_agg(row_to_json(x)),'[]'::json) FROM (SELECT p.revision_id,p.profile_version_id,p.match_team_revision_id,p.participation_evidence,p.recorded_from_gen,r.locator,d.legacy_object_path,d.content_sha256
   FROM football.match_players_current p LEFT JOIN ingest.source_records r ON r.id=p.source_record_id LEFT JOIN ingest.source_documents d ON d.id=r.document_id
   WHERE p.match_id=ma.match_id AND p.player_id=pa.player_id AND p.team_id=ta.team_id ORDER BY p.revision_id LIMIT 4) x) exact_cohort
 FROM wanted w LEFT JOIN ingest.public_aliases_current ma ON ma.route_kind='match' AND ma.public_key=w.match_key
 LEFT JOIN ingest.public_aliases_current pa ON pa.route_kind='player' AND pa.public_key=w.actor
 LEFT JOIN ingest.public_aliases_current ta ON ta.route_kind='team' AND ta.public_key=w.team_key ORDER BY w.shot_key""",wanted_params,4)
        shots=query('exact_shot_identity_and_source_locator',wanted_sql+"""SELECT w.*,s.id shot_id,s.revision_id,s.match_id,s.team_id,s.player_id,s.player_profile_version_id,s.source_record_id,s.source_ordinal,s.recorded_from_gen,r.locator sql_locator,d.legacy_object_path,d.content_sha256
 FROM wanted w LEFT JOIN LATERAL (SELECT s.* FROM football.shots s JOIN ingest.source_records r ON r.id=s.source_record_id JOIN ingest.source_documents d ON d.id=r.document_id
  WHERE s.external_shot_id=w.shot_key AND r.locator=w.locator AND d.legacy_object_path=%s AND d.content_sha256=%s ORDER BY s.id LIMIT 2) s ON true
 LEFT JOIN ingest.source_records r ON r.id=s.source_record_id LEFT JOIN ingest.source_documents d ON d.id=r.document_id ORDER BY w.shot_key""",(*wanted_params,DOCUMENT,SHA),4)
        c.commit();report.update(status='pass_metadata_readback',globalActors=actors,exactCohorts=cohorts,exactShots=shots,
            sourceRowDigestRecomputed=False,limits=['Exact cohort absence does not imply global identity absence','Supplied raw-row digest is a witness, not recomputed by these SQL metadata reads'])
    except BaseException as error:
        report.update(status='fail',errorType=type(error).__name__,sqlstate=getattr(error,'sqlstate',None))
    finally:
        if c is not None:c.close()
        report['connectionClosed']=c is None or c.closed;report['elapsedMs']=round((time.monotonic()-started)*1000,3)
        report['sourceCheckpointSha256']=sha(SOURCE/'checkpoint.json');report['sourceNativeEvidenceSha256']=sha(SOURCE/'native94-before.json');report['scriptSha256']=sha(Path(__file__))
        save(run/'result.json',report);print(json.dumps({'status':report['status'],'selects':report['selects'],'decodedBytes':report['decodedBytes'],'evidence':str(run/'result.json')}))
    return 0 if report['status']=='pass_metadata_readback' else 1

if __name__=='__main__':raise SystemExit(main())
