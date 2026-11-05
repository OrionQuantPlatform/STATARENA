"""Independent assertions for the declared synthetic workflow, not a publisher."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
import re
from urllib.parse import urlencode
from workflow_budget import LIMITS,digest


def qs(**values):return urlencode({k:v for k,v in values.items() if v is not None})


def snapshot(conn,model):
    active=[t['qualified_name'] for s in model['schemas'] for t in s['tables'] if t['phase']!='models']
    # Trusted canonical model identifiers only. No source SQL/table name is used.
    canonical_bytes=(Path(__file__).resolve().parents[2]/'architecture/orion-plan-20261104/target-schema.proposed.json').read_bytes()
    assert hashlib.sha256(canonical_bytes).hexdigest()=='18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08'
    canonical=json.loads(canonical_bytes)
    canonical_names=[t['qualified_name'] for s in canonical['schemas'] for t in s['tables'] if t['phase']!='models']
    assert len(active)==len(set(active))==94 and active==canonical_names,'Only the exact94 canonical model names may enter snapshot SQL'
    assert all(re.fullmatch(r'(ingest|football|analytics)\.[a-z_][a-z0-9_]*',q) for q in active)
    rows=conn.execute(' UNION ALL '.join(f"SELECT '{q}',count(*),md5(coalesce(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text)),'')) FROM {q} t" for q in active)).fetchall()
    counts={r[0]:r[1] for r in rows};table_digests={r[0]:r[2] for r in rows}
    builds=conn.execute('SELECT id,competition_season_id,status,dataset_snapshot_id,catalog_snapshot_id,dependencies_sha256,representation_version FROM analytics.aggregation_builds ORDER BY id').fetchall()
    pointers=conn.execute('SELECT competition_season_id,build_id,catalog_snapshot_id,published_from_gen,published_to_gen,representation_version FROM analytics.publication_versions ORDER BY competition_season_id,published_from_gen').fetchall()
    dirty=conn.execute('SELECT competition_season_id,generation,competition_season_revision_id FROM ingest.dirty_editions ORDER BY competition_season_id').fetchall()
    seq=conn.execute('SELECT last_value,is_called FROM ingest.commit_generation_seq').fetchone()
    actual={'typedRows':sum(counts.values()),'builds':counts['analytics.aggregation_builds'],'matchSummaries':counts['analytics.match_summary'],
      'editionSummaries':counts['analytics.competition_summary'],'generations':counts['ingest.dataset_snapshots'],'publications':counts['analytics.publication_versions']}
    for key,value in actual.items():assert value<=LIMITS[key],f'{key} exceeds budget: {value}'
    return {'counts':counts,'tableDigests':table_digests,'caps':actual,'builds':[list(x) for x in builds],'pointers':[list(x) for x in pointers],
      'dirty':[list(x) for x in dirty],'sequence':list(seq)}


def active_builds(conn):
    rows=conn.execute('SELECT p.competition_season_id,b.id,b.dataset_snapshot_id,b.catalog_snapshot_id,b.dependencies_sha256,d.generation,c.generation FROM analytics.publication_versions p JOIN analytics.aggregation_builds b ON b.id=p.build_id JOIN ingest.dataset_snapshots d ON d.id=b.dataset_snapshot_id JOIN ingest.dataset_snapshots c ON c.id=b.catalog_snapshot_id WHERE p.published_to_gen IS NULL ORDER BY 1').fetchall()
    return {r[0]:{'build':r[1],'datasetSnapshot':r[2],'catalogSnapshot':r[3],'dependencies':r[4],'dg':r[5],'cg':r[6]} for r in rows}


def expected_products(conn,inputs):
    counters={'A':(3,2,2,1),'B':(1,1,2,2),'C':(1,1,2,1)}
    builds=active_builds(conn);assert len(builds)==3,builds
    expected={}
    for key,edition in inputs.editions.items():
        eid=edition['id'];b=builds[eid]
        assert b['dg']<=inputs.data_generation and b['cg']<=inputs.catalog_generation
        assert len(b['dependencies'])==64
        rows=conn.execute('SELECT match_id,match_revision_id,match_date,kickoff_at,status,home_team_id,away_team_id,home_label,away_label,home_goals,away_goals,score_scope,home_shootout_goals,away_shootout_goals FROM analytics.match_summary WHERE build_id=%s ORDER BY match_id',(b['build'],)).fetchall()
        wants=[(mid,w) for mid,w in inputs.expected.items() if w['key']==key]
        assert len(rows)==len(wants)
        by_id={r[0]:r for r in rows}
        for mid,w in wants:
            m=inputs.match_rows[mid];r=by_id[m['id']];sides=inputs.sides[mid]
            assert r[1]==m['revision_id'] and (r[2].isoformat() if r[2] else None)==w['date'] and r[3] is None
            assert (r[4],r[5],r[6],r[7],r[8])==(w['status'],sides['home']['team_id'],sides['away']['team_id'],'home observed label','away observed label')
            assert (r[9],r[10],r[11],r[12],r[13])==(w['home'],w['away'],'final_without_shootout' if w['home'] is not None else None,w['homePenalty'],w['awayPenalty'])
        summary=conn.execute('SELECT matches_count,finished_matches_count,teams_count,players_count,goals FROM analytics.competition_summary WHERE build_id=%s AND competition_season_id=%s',(b['build'],eid)).fetchone()
        assert summary==(*counters[key],None),(key,summary)
        expected[key]={'build':b,'independentCounterValues':list(counters[key]),'rows':len(rows)}
    return expected


def tokens(manifest):
    return {k:next(e['representationToken'] for e in manifest['editions'] if e['season']==season)
      for k,season in [('A','2024/2025'),('B','2025/2026'),('C','2026/2027')]}


def paths(key,token):
    season={'A':'2024/2025','B':'2025/2026','C':'2026/2027'}[key]
    mid={'A':'m_000001','B':'m_000004','C':'m_000005'}[key]
    return ['/api/dashboard/manifest?'+qs(v=token),'/api/fixtures?'+qs(v=token,league='l_000001',season=season,limit=2),
      f'/api/matches/{mid}/summary?'+qs(v=token),f'/api/pitchapi/matches/{mid}/shots?'+qs(v=token)]


def same_http(before,after):
    assert (before['status'],before['body'])==(after['status'],after['body'])
    volatile={'date','server-timing','connection','keep-alive'}
    assert {k:v for k,v in before['headers'].items() if k not in volatile}=={k:v for k,v in after['headers'].items() if k not in volatile}


def metadata_only(response):
    heavy=re.compile(r'\bfootball\.(shots|match_heatmaps|match_heatmap_cells|pass_networks|pass_network_nodes|pass_network_edges)\b',re.I)
    assert not any(heavy.search(q['sql'] or '') or re.search(r'/\*orion:(list|summary|shots)\*/',q['sql'] or '') for q in response['sql'])


def bounded_light_list(response,limit):
    heavy=re.compile(r'\bfootball\.(shots|match_heatmaps|match_heatmap_cells|pass_networks|pass_network_nodes|pass_network_edges)\b',re.I)
    assert len(response['sql'])<=5
    assert not any(heavy.search(q['sql'] or '') for q in response['sql'])
    materialized=[q for q in response['sql'] if '/*orion:list*/' in (q['sql'] or '')]
    assert len(materialized)==1 and materialized[0]['resultRows']<=limit+1


def summary_http(response,inputs,mid):
    assert response['status']==200
    value=response['value']['data']['match'];want=inputs.expected[mid]
    assert value['summaryVersion']==1 and value['shots']==[] and value['stats']==[] and value['leadingPlayers']==[]
    assert value['id']==mid and value['date']==want['date'] and value['timeUtc'] is None and value['status']==want['status']
    for side in ['home','away']:
        assert value[side]['score']==want[side] and value[side]['scorePenalty']==want[side+'Penalty']
        assert value[side]['name']==want[side+'Name'] and value[side]['imageUrl'] is None
    assert value['coverageStates']['shots']==want['shots']
    assert not any(re.search(r'\bfootball\.(shots|match_heatmaps|pass_networks)\b',q['sql'] or '') for q in response['sql'])


def no_begin_generation(worker_trace,offset):
    lines=Path(worker_trace).read_text().splitlines()[offset:] if Path(worker_trace).exists() else []
    assert not any('ingest.begin_generation' in json.loads(line)['sql'].replace('"','').lower() for line in lines)
