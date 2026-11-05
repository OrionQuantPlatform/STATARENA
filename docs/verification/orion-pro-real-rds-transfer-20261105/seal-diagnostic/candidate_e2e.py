#!/usr/bin/env python3
"""Precode artifact E2E for a non-applied SQL candidate. No database access."""
from datetime import datetime,timezone
import hashlib,json,sys,traceback
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
ORIGINAL=ROOT/'dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql'
CANDIDATE=BASE/'candidate_metric_membership_guard.sql'
SHA='e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6'
LINES=[241,242,243]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    run=BASE/'candidate-e2e-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
    report={'kind':'nonapplied_metric_guard_candidate_structural_e2e_v1','command':[sys.executable,str(Path(__file__))],'expected':str(BASE/'PROPOSAL.md'),
            'databaseConnections':0,'sourceCalls':0,'businessWrites':[],'candidateSqlExecuted':False,'fullAcceptance':False,'cases':[],'inputSha256':{}}
    for p in [Path(__file__),BASE/'PROPOSAL.md',ORIGINAL,CANDIDATE]:
        if p.is_file():
            report['inputSha256'][str(p.relative_to(ROOT))]=sha(p);(run/'inputs'/p.name).write_bytes(p.read_bytes())
    block=None
    for name in ['sealed014_exact','candidate_available','three_exact_necessary_guards','all_other_bytes_preserved']:
        if block:report['cases'].append({'case':name,'status':'unverified','reason':block});continue
        try:
            if name=='sealed014_exact':assert sha(ORIGINAL)==SHA;actual={'originalSha256':SHA}
            elif name=='candidate_available':assert CANDIDATE.is_file(),'Non-applied SQL candidate absent (expected precode RED)';actual={'candidateSha256':sha(CANDIDATE)}
            elif name=='three_exact_necessary_guards':
                original=ORIGINAL.read_text().splitlines(keepends=True);candidate=CANDIDATE.read_text().splitlines(keepends=True);assert len(original)==len(candidate)
                changed=[i+1 for i,(a,b) in enumerate(zip(original,candidate)) if a!=b];assert changed==LINES,changed
                proofs=[]
                for line in LINES:
                    old=original[line-1].rstrip('\n');new=candidate[line-1].rstrip('\n')
                    start='IF EXISTS (';end=") THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE=";assert old.startswith(start)
                    body,suffix=old[len(start):].rsplit(end,1);assert body.endswith(')')
                    selected_prefix,selected=body.rsplit(' AND NOT EXISTS (',1);assert selected.endswith(')');selected=selected[:-1]
                    parent=selected_prefix.split(' child JOIN ',1)[1].split(' anchor ON ',1)[0]
                    guard='SELECT 1 FROM '+parent+' anchor WHERE NOT EXISTS ('+selected+')'
                    expected='IF (CASE WHEN EXISTS ('+guard+') THEN EXISTS ('+body+') ELSE false END) THEN RAISE EXCEPTION USING ERRCODE=\'23514\', MESSAGE='+suffix
                    assert new==expected,'Original predicate or NULL semantics changed'
                    proofs.append({'line':line,'originalQuerySha256':hashlib.sha256(body.encode()).hexdigest(),'necessaryParentGuardSha256':hashlib.sha256(guard.encode()).hexdigest()})
                actual={'changedLines':changed,'proofs':proofs,'equivalence':'old_exists implies parent_guard_exists; original predicates retained exactly'}
            else:
                restored=list(candidate)
                for line in LINES:restored[line-1]=original[line-1]
                assert ''.join(restored).encode()==ORIGINAL.read_bytes()
                assert ORIGINAL.read_text().count('RAISE EXCEPTION')==CANDIDATE.read_text().count('RAISE EXCEPTION')
                actual={'originalRestoredByteExact':True,'exceptionCount':ORIGINAL.read_text().count('RAISE EXCEPTION'),'otherBytesChanged':0}
            report['cases'].append({'case':name,'status':'pass','actual':actual})
        except BaseException as error:
            block=name+': '+str(error);report['cases'].append({'case':name,'status':'fail','error':str(error),'traceback':traceback.format_exc()})
    for case in ['postgresql_null_and_closed_interval_equivalence','dense_8second_seal_and_deferred_commit','real_target_performance']:
        report['cases'].append({'case':case,'status':'unverified','reason':'No PostgreSQL/candidate execution authorized by this structural workflow'})
    report['status']='fail' if block else 'prepared_nonapplied_structural_only';report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']}
    (run/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
    return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
