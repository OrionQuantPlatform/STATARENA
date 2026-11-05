#!/usr/bin/env python3
"""Precode exact source/reconstruction gate for the proposed 018 SQL candidate."""
from datetime import datetime, timezone
import hashlib, json, shutil, sys, traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]
PINS=BASE/'PINS.json'
PINS_SHA='03cf000c7340c6e93d60dc98debff018f627d99089ec2409d6a17651fa61b194'
SQL=ROOT/'dashboard/backend/migrations'
CANDIDATE=BASE/'candidate_018.sql'
START='CREATE OR REPLACE FUNCTION "ingest"."validate_generation"(g bigint) RETURNS void\n'
END='$orion_pro$;'
MARKER_START='-- 018 metric history fast path\n'
MARKER_END='-- 018 end metric history fast path\n'
CASES=('exact017_parent_and_captured_overlap','implementation_available','sole_guard_and_optional_index_delta',
       'preserved_original_sql_and_native107','matched_owned_runtime_not_executed')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parent_body(text):
    assert text.count(START)==1,'Expected one exact parent validator'
    at=text.index(START);end=text.index(END,at)+len(END)
    return text[at:end]+'\n'

def main():
    assert not sys.flags.optimize
    run=BASE/'static-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
    report={'kind':'precode_metric_overlap018_static_e2e_v1','command':[sys.executable,str(Path(__file__))],
            'expected':str(BASE/'PROPOSAL.md'),'cases':[],'pgStarts':0,'sourceReads':0,'ramGets':0,'rdsCalls':0,
            'businessWrites':0,'fullAcceptance':False}
    for p in [Path(__file__),PINS,BASE/'PROPOSAL.md',CANDIDATE]:
        if p.is_file():shutil.copy2(p,run/'inputs'/p.name)
    block=None;baseline=original=candidate=None
    for name in CASES:
        if block:report['cases'].append({'case':name,'status':'unverified','reason':block});continue
        try:
            if name==CASES[0]:
                assert sha(PINS)==PINS_SHA
                pins=json.loads(PINS.read_text())
                assert all(sha(ROOT/p)==h for p,h in pins['files'].items())
                a=(SQL/'015_orion_pro_metric_membership_guard.sql').read_text().splitlines(keepends=True)
                b=(SQL/'016_orion_pro_native_match_details.sql').read_text()
                c=(SQL/'017_orion_pro_native_match_core_fields.sql').read_text()
                original=''.join(b.splitlines(keepends=True)[1433:1435]);baseline=parent_body(b)
                assert ''.join(a[154:156])==original and START not in c and original in baseline
                assert hashlib.sha256(original.encode()).hexdigest()==pins['originalOverlapSqlSha256']
                assert baseline.count('PERFORM ingest.validate_native107_generation(g);')==1
                assert all(x['unique'] and x['immediate'] and x['valid'] for x in pins['nativeImmediateUniqueIndexes'])
                actual={'oldPairSha256':pins['originalOverlapSqlSha256'],'exact016ParentSha256':hashlib.sha256(baseline.encode()).hexdigest(),
                        'optionalIndexNotYetInstalled':True,'actualRollbackMetricRelationBytes':pins['actualRollbackMetricRelationBytes']}
            elif name==CASES[1]:
                assert CANDIDATE.is_file(),'018 SQL candidate absent (expected precode RED)'
                candidate=CANDIDATE.read_text()
                actual={'candidateSha256':sha(CANDIDATE)}
            elif name==CASES[2]:
                fn=parent_body(candidate)
                assert fn.count(MARKER_START)==fn.count(MARKER_END)==1
                a,tail=fn.split(MARKER_START);delta,b=tail.split(MARKER_END)
                assert delta.count(original)==1
                prefix,suffix=delta.split(original)
                assert prefix.strip().startswith('IF CASE WHEN') and suffix.strip()=='END IF;'
                assert all(token in prefix for token in ['pg_index','to_regclass','indisunique','indimmediate','indisvalid',
                    'indisready','indislive','pg_get_indexdef','recorded_to_gen IS NOT NULL','ORDER BY recorded_to_gen','LIMIT 1','ELSE true'])
                ddl,_,tail=candidate.partition(fn)
                index='CREATE INDEX football_player_match_metric_values_sv_closed_probe_idx\n  ON football.player_match_metric_values USING btree (recorded_to_gen)\n  WHERE recorded_to_gen IS NOT NULL;'
                assert not tail.strip() and ddl.strip() in ('',index),'Only the optional exact partial index is permitted'
                actual={'oneGuard':True,'candidateIndex':bool(ddl.strip()),'originalQueryTextRetained':True}
            elif name==CASES[3]:
                assert a+original+b==baseline,'Removing the guard did not restore the exact parent function'
                assert fn.count('PERFORM ingest.validate_native107_generation(g);')==1
                actual={'parentByteIdenticalWithoutEnvelope':True,'exactFallbackOrderAndMessages':True}
            else:
                report['cases'].append({'case':name,'status':'unverified','reason':'Separate ROOT release required for owned PostgreSQL'});continue
            report['cases'].append({'case':name,'status':'pass','actual':actual})
        except BaseException as e:
            block=name;report['cases'].append({'case':name,'status':'fail','error':str(e),'traceback':traceback.format_exc()})
    report['status']='fail' if block else 'pass_static_only'
    report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ('pass','fail','unverified')}
    (run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
    return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
