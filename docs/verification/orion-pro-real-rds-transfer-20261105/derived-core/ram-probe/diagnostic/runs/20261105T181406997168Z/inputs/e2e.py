#!/usr/bin/env python3
"""Before-code symbolic decoder workflow, no source access."""
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,importlib.util,json,pickle,shutil,sys,time,traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
MODULE=BASE/'symbols.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class ForbiddenFixture:
    def __reduce__(self):
        return eval,("'sensitive-canary-not-to-be-retained'",)
def main():
    run=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
    result={'kind':'symbolic_ram_diagnostic_source_free_e2e_v1','command':[sys.executable,str(Path(__file__))],
            'expected':str(BASE/'PROTOCOL.md'),'cases':[],'sourceCalls':0,'ramGets':0,'reductionsExecuted':0,'fullAcceptance':False}
    for p in [Path(__file__),BASE/'PROTOCOL.md',MODULE,BASE/'PINS.json']:
        if p.is_file():shutil.copy2(p,run/'inputs'/p.name)
    block=None;m=None
    for case in ('implementation_available','symbolic_wire_global_names','trailing_wire_refused'):
        if block:result['cases'].append({'case':case,'status':'unverified','reason':block});continue
        try:
            if case=='implementation_available':
                assert MODULE.is_file(),'Symbol-only candidate absent (expected precode RED)'
                spec=importlib.util.spec_from_file_location('ram_symbols_offline',MODULE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
                actual={'moduleSha256':sha(MODULE)}
            elif case=='symbolic_wire_global_names':
                body=pickle.dumps({'irrelevant-token':'business-canary-not-persisted','t':datetime(2032,1,1,tzinfo=timezone.utc),
                                   'n':[Decimal('1.25'),Decimal('2.5')],'x':[ForbiddenFixture(),ForbiddenFixture()]},protocol=5)
                actual=m.inventory_symbols(body,deadline=time.monotonic()+10)
                names={(x['module'],x['name'],x['allowedInV2']) for x in actual['globals']}
                assert ('builtins','eval',False) in names and ('decimal','Decimal',True) in names and ('datetime','datetime',True) in names
                assert actual['reductionsExecuted']==0 and actual['dataDecoded'] is False
                assert 'canary' not in json.dumps(actual)
            else:
                try:m.inventory_symbols(pickle.dumps({},protocol=5)+b'trailing',deadline=time.monotonic()+10)
                except m.v1.Refusal as error:assert error.code=='WIRE_TRAILING';actual={'reasonCode':error.code}
                else:raise AssertionError('Unexpected trailing wire acceptance')
            result['cases'].append({'case':case,'status':'pass','actual':actual})
        except BaseException as error:
            block=case;result['cases'].append({'case':case,'status':'fail','error':str(error),'traceback':traceback.format_exc()})
    result['status']='fail' if block else 'pass_source_free_only'
    result['counts']={s:sum(c['status']==s for c in result['cases']) for s in ['pass','fail','unverified']}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'counts':result['counts'],'evidence':str(run/'result.json')}))
    return 1 if block else 0
if __name__=='__main__':raise SystemExit(main())
