"""D24–D28 SQL workflows for the separately approved017, before its compiler."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
MIG=ROOT/'dashboard/backend/migrations/017_orion_pro_native_match_core_fields.sql'
MODEL=ROOT/'docs/architecture/orion-native-details-107-20261105/target-schema.approved-107-core.json'
TABLE='football.match_observation_details'
FIELDS=['source_referee_label','source_referee_state','source_has_playoff','source_has_playoff_state','source_league_image_url','source_league_image_url_state']


def observation(c,label,fields):
    source=c.fx.ids['source']
    dataset=c.ingest.execute('SELECT id FROM ingest.source_datasets WHERE source_id=%s ORDER BY id LIMIT 1',(source,)).fetchone()[0]
    doc,_=c.fx._record(source,dataset,label)
    rec=c.fx.record(label+'_source',doc,'/data',external='m_000001')
    match=c.fx.match_rows['m_000001']
    return c.fx._insert(TABLE,source_record_id=rec['id'],match_id=match['id'],match_revision_id=match['revision_id'],
        source_match_key='m_000001',source_date_text='2026-11-04',source_venue_label='',resolution_state='resolved',**fields)


def D24(c):
    return c.expect_sqlstate('old016_core_fields_unavailable',lambda:c.db.execute('SELECT source_referee_label FROM '+TABLE+' LIMIT 0'),{'42703'})


def D25(c):
    with c.fx._generation('before017_core_observation'):
        legacy=observation(c,'owned017_old_core',{})
    sql=MIG.read_text();digest=hashlib.sha256(sql.encode()).hexdigest()
    def apply():
        rows=c.db.execute('SELECT version,content_sha256 FROM ingest.schema_migrations ORDER BY version').fetchall()
        if rows[-1]==('017',digest):return 'verified_noop'
        assert [r[0] for r in rows]==['012','013','014','015','016']
        c.db.execute(sql,prepare=False)
        c.db.execute("INSERT INTO ingest.schema_migrations VALUES('017',%s,CURRENT_TIMESTAMP,'owned_017_workflow')",(digest,))
        return 'applied'
    before=c.catalogue();old_rows=c.rows()
    with c.db.transaction(force_rollback=True):assert apply()=='applied'
    assert before==c.catalogue() and old_rows==c.rows()
    with c.db.transaction():assert apply()=='applied'
    value=c.runtime.execute('SELECT '+','.join(FIELDS)+' FROM '+TABLE+' WHERE source_record_id=%s',(legacy['source_record_id'],)).fetchone()
    assert value==(None,'unrecorded',None,'unrecorded',None,'unrecorded'),value
    prior=c.runtime.execute('SELECT '+','.join(legacy)+' FROM '+TABLE+' WHERE source_record_id=%s',(legacy['source_record_id'],)).fetchone()
    assert list(prior)==list(legacy.values())
    totals=c.db.execute("""WITH t AS (SELECT c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE c.relkind='r' AND n.nspname IN ('football','ingest','analytics'))
      SELECT (SELECT count(*) FROM t),(SELECT count(*) FROM pg_attribute a JOIN t ON t.oid=a.attrelid WHERE a.attnum>0 AND NOT a.attisdropped),
      (SELECT count(*) FROM pg_constraint c JOIN t ON t.oid=c.conrelid WHERE c.contype='f')""").fetchone()
    assert totals==(98,1829,447)
    after=c.catalogue()
    with c.db.transaction():assert apply()=='verified_noop'
    assert after==c.catalogue()
    c.fx.model=json.loads(MODEL.read_text());c.fx.tables={t['qualified_name']:t for s in c.fx.model['schemas'] for t in s['tables']}
    return {'nativeTotals':totals,'legacyStates':value,'retainedOldPhysicalObservation':legacy['source_record_id'],
            'rollbackExact':True,'journalNoop':True,'migrationSha256':digest}


def D26(c):
    outcomes=[]
    for label,fields,wanted in [
        ('native_values',dict(source_referee_label='',source_referee_state='value',source_has_playoff=False,source_has_playoff_state='value',source_league_image_url='https://media.fixture.invalid/competition.png',source_league_image_url_state='value'),('', 'value',False,'value','https://media.fixture.invalid/competition.png','value')),
        ('native_presence',dict(source_referee_state='null',source_has_playoff_state='absent',source_league_image_url='',source_league_image_url_state='value'),(None,'null',None,'absent','','value')),
    ]:
        with c.fx._generation(label):row=observation(c,label,fields)
        actual=c.runtime.execute('SELECT '+','.join(FIELDS)+' FROM '+TABLE+' WHERE source_record_id=%s',(row['source_record_id'],)).fetchone()
        assert actual==wanted;outcomes.append(actual)
    refused=[]
    for n,value,state,fields in [(0,FIELDS[0],FIELDS[1],{FIELDS[0]:'',FIELDS[1]:'absent'}),
                                  (1,FIELDS[2],FIELDS[3],{FIELDS[3]:'value'}),
                                  (2,FIELDS[4],FIELDS[5],{FIELDS[5]:'unsupported'})]:
        label='bad_core_pair_'+str(n)
        def invalid():
            prior=c.fx.g;c.fx.g=c.fx._begin(label)
            try:observation(c,label,fields)
            finally:c.fx.g=prior
        refused.append(c.expect_sqlstate(label,invalid,{'23514'},'match_observation_'+state+'_ck',c.ingest))
    return {'exactRuntimeValues':outcomes,'pairRefusals':refused,'httpQualification':False}


def D27(c):
    before=c.runtime.execute('SELECT count(*) FROM '+TABLE).fetchone()[0]
    assert before>=3
    cases={}
    for name,connection,stmt,state in [
        ('owner_change',c.db,'UPDATE '+TABLE+' SET source_has_playoff=true','55000'),
        ('owner_delete',c.db,'DELETE FROM '+TABLE,'55000'),
        ('ingest_change',c.ingest,'UPDATE '+TABLE+' SET source_referee_label=NULL','42501'),
        ('late_observation',c.ingest,'INSERT INTO '+TABLE+' SELECT * FROM '+TABLE+' LIMIT 1','55000'),
    ]:cases[name]=c.expect_sqlstate(name,lambda:connection.execute(stmt),{state},conn=connection)
    assert c.runtime.execute('SELECT count(*) FROM '+TABLE).fetchone()[0]==before
    return cases


def D28(c):
    legacy=c.fx.corrected_builds['A']
    def build(metrics,transform):
        c.fx.aggregation_binding=(metrics,transform)
        try:return c.fx.build('A',c.fx.data2,c.fx.catalog2)
        finally:c.fx.aggregation_binding=None
    older=build('orion_pro_native107_v1','orion_pro_publish_native107_v1')
    newer=build('orion_pro_native107_core_v1','orion_pro_publish_native107_core_v1')
    c.fx.publish({'A':older},'owned_native016_current')
    c.fx.publish({'A':newer},'owned_native017_current')
    for old in [older,legacy]:
        try:c.fx.publish({'A':old},'owned_refused_downgrade')
        except c.driver.Error as error:
            assert error.sqlstate=='23514' and 'native107: publication cannot downgrade' in error.diag.message_primary,str(error)
        else:raise AssertionError('Old build replaced current017')
    retained=c.runtime.execute('SELECT build_id,published_to_gen FROM analytics.publication_versions WHERE build_id IN (%s,%s) ORDER BY build_id',(older,newer)).fetchall()
    assert len(retained)==2 and retained[0][0]==older and retained[0][1] is not None and retained[1]==(newer,None),retained
    return {'oldNativeRetained':older,'currentNative017':newer,'bothDowngradesRefused':True,'fixtureMetadataOnly':True,'realPublisherQualified':False}


CORE_CASES=[D24,D25,D26,D27,D28]
