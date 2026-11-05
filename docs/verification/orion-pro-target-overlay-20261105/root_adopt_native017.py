#!/usr/bin/env python3
"""Once-only adoption of the two exact user-approved migrations on existing RDS."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import sys
import tempfile
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
POLICY = ROOT/'docs/verification/orion-pro-policy-rds-20261105'
ROLLBACK = ROOT/'docs/verification/orion-pro-real-rds-transfer-20261105/failed-core-p2-readbacks/20261105T171021459489Z'
OWNED = BASE/'runs/20261105T174639690726Z-approved-overlay-owned-v1/result.json'
STATE = 'ff1f3a336bfde1067b2b70e0fc6d3517f4d648631c2813374bca04cd4fddf189'
NATIVE = '5421c7a3457c36d133785ad79185e3f54f8948edf58078d495258c4d105f1753'
HOST = 'statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'
DB = 'statarena_prod'
ACTOR = 'statarena_admin'
LEASES = ('20261104,2', '20261104,1', '97813003::bigint')


class GateError(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise GateError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path, expected, cap=8*1024**2):
    require(isinstance(expected,str) and re.fullmatch('[a-f0-9]{64}',expected),'exact metadata pin required')
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as file:
        s=os.fstat(file.fileno())
        require(stat.S_ISREG(s.st_mode) and s.st_size<=cap,'bounded regular metadata required')
        raw=file.read(cap+1)
    require(len(raw)<=cap and hashlib.sha256(raw).hexdigest()==expected,'metadata bytes differ')
    def unique(items):
        r={}
        for k,v in items:
            require(k not in r,'duplicate metadata key')
            r[k]=v
        return r
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:require(False,'nonfinite metadata'))


def save(path,value):
    with Path(path).open('x') as out:
        out.write(json.dumps(value,indent=2,default=str)+'\n')


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--preflight',action='store_true')
    modes.add_argument('--adopt',action='store_true')
    parser.add_argument('--release',type=Path);parser.add_argument('--release-sha256')
    args=parser.parse_args()
    report={'kind':'root_actual_native017_adoption_v1','status':'offline_plan','connections':0,'awsCalls':0,
            'sportSourceCalls':0,'businessWrites':0,'readStatements':0,'ddlAttempted':False,'fullAcceptance':False}
    if not (args.preflight or args.adopt):
        if args.release or args.release_sha256:parser.error('Explicit operation mode required')
        print(json.dumps(report));return 0
    started=time.monotonic()
    clients=[]
    out=private=None
    try:
        require(not sys.flags.optimize and not any(k.startswith('PG') for k in os.environ),'closed libpq environment required')
        require(args.release and args.release.is_absolute() and args.release.parent==BASE,'separate absolute release required')
        spec=read(args.release,args.release_sha256,16384)
        mode='adopt' if args.adopt else 'preflight'
        overlay_path=ROOT/'dashboard/scripts/orion_pro_target_overlay.py'
        exact={'kind':'root_actual_native017_operation_release_v1','approvedBy':'ROOT','mode':mode,
               'target':{'hostname':HOST,'port':5432,'database':DB,'actor':ACTOR,'engine':180006,'tls':'verify-full'},
               'operatorSha256':sha(__file__),'overlaySha256':sha(overlay_path),'protocolSha256':sha(BASE/'RDS_ADOPTION_PROTOCOL.md'),
               'nativeBaselineSha256':NATIVE,'baselineStateSha256':STATE,'ownedProofSha256':sha(OWNED),
               'maximumSeconds':150,'maximumConnections':2 if args.adopt else 1,
               'approvedMigrations':['016','017'],'businessWrites':0,'productionActivation':False,'fullAcceptance':False}
        specific={'preflightPath','preflightSha256'} if args.adopt else set()
        require(set(spec)==set(exact)|{'allocationId','expiresAt','codeCommit'}|specific and
                all(spec[k]==v for k,v in exact.items()) and
                re.fullmatch('[a-zA-Z0-9-]{1,70}',spec['allocationId']) and
                re.fullmatch('[a-f0-9]{40}',spec['codeCommit']), 'exact native017 release required')
        expiry=datetime.fromisoformat(spec['expiresAt'])
        require(expiry.tzinfo is not None and datetime.now(timezone.utc)<expiry,'expired release')
        owned=read(OWNED,spec['ownedProofSha256'])
        require(owned['status']=='pass_owned_only' and owned['counts']=={'pass':9,'fail':0,'unverified':0} and
                owned['inputsExact'] and owned['connectionsClosed'] and owned['cleanup']['server_stopped'] and
                owned['cleanup']['owned_directory_removed'] and owned['inputHashes'][str(overlay_path.relative_to(ROOT))]==spec['overlaySha256'] and
                owned['sourceCalls']==owned['rdsCalls']==0,'exact complete owned proof required')
        baseline=read(ROLLBACK/'native.json',NATIVE)
        prepared=None
        if args.adopt:
            pre=ROOT/spec['preflightPath']
            require(pre.resolve().is_relative_to(BASE/'rds-runs') and pre.name=='result.json','owned preflight path required')
            prepared=read(pre,spec['preflightSha256'])
            require(prepared['status']=='verified_readonly_015' and prepared['nativeStateSha256']==STATE and
                    prepared['operatorSha256']==spec['operatorSha256'] and prepared['overlaySha256']==spec['overlaySha256'] and
                    prepared['codeCommit']==spec['codeCommit'] and prepared['privateAuthRemoved'] and
                    prepared['connectionsClosed'] and not prepared['ddlAttempted'],'exact readonly preflight required')
        out=BASE/'rds-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        save(BASE/(spec['allocationId']+'.consumed.json'),{'releaseSha256':args.release_sha256,'result':str((out/'result.json').relative_to(ROOT))})
        out.mkdir(parents=True)
        save(out/'release.json',spec)
        report.update(status='in_progress',mode=mode,command=[sys.executable,str(Path(__file__)),*sys.argv[1:]],
                      expected=str(BASE/'RDS_ADOPTION_PROTOCOL.md'),releaseSha256=args.release_sha256,
                      operatorSha256=spec['operatorSha256'],overlaySha256=spec['overlaySha256'],codeCommit=spec['codeCommit'])
        def expired(_sig,_frame):raise TimeoutError('150-second native017 operation limit')
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,145)
        sys.path.insert(0,str(ROOT/'dashboard/scripts'))
        require(sha(POLICY/'adapter.py')=='a6e5213e54de057562b10f57b4dd675e1501b4dd82449dd7a3ab19e7caf250d6','original observer differs')
        observer=load(POLICY/'adapter.py','native017_original_observer')
        require(observer.state_hash(baseline)==STATE,'original native state differs')
        import orion_pro_target_overlay as overlay
        aws=load(POLICY/'root_readonly.py','native017_aws_auth').aws
        identity=aws('sts','get-caller-identity');report['awsCalls']+=1
        require(identity['Account']=='361769570630' and identity['Arn']=='arn:aws:iam::361769570630:user/hugo.lemonnier','AWS identity differs')
        secret=json.loads(aws('ssm','get-parameter','--name','/statarena/app/rds-admin','--with-decryption')['Parameter']['Value'])
        report['awsCalls']+=1
        password=secret.get('password')
        require((secret.get('username') or secret.get('user'))==ACTOR and isinstance(password,str) and password and
                not any(c in password for c in '\r\n\x00'),'existing private authentication differs')
        with tempfile.TemporaryDirectory(prefix='orion-native017-auth-',dir='/tmp') as folder:
            private=Path(folder);private.chmod(0o700)
            passfile=private/'auth.pgpass'
            def escaped(v):return str(v).replace('\\','\\\\').replace(':','\\:')
            with os.fdopen(os.open(passfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as file:
                file.write(':'.join(escaped(x) for x in (HOST,5432,DB,ACTOR,password))+'\n')
            del secret,password
            observer.validated_rds_passfile({'ORION_RDS_PASSFILE':str(passfile)})
            addresses=sorted({row[4][0] for row in socket.getaddrinfo(HOST,5432,type=socket.SOCK_STREAM)})
            require(addresses,'existing RDS DNS absent')
            import psycopg
            class Counted:
                def __init__(self, raw):self.raw=raw
                def __getattr__(self,key):return getattr(self.raw,key)
                def __enter__(self):self.raw.__enter__();return self
                def __exit__(self,*exc):return self.raw.__exit__(*exc)
                def execute(self,sql,*params,**options):
                    if sql.lstrip().upper().startswith(('SELECT','WITH')):
                        report['readStatements']+=1
                        require(report['readStatements']<=48,'read statement allocation exceeded')
                    return self.raw.execute(sql,*params,**options)
            def connect():
                require(len(clients)<spec['maximumConnections'],'connection allocation exceeded')
                c=psycopg.connect(**observer._rds_connection_kwargs(str(passfile),addresses[0]))
                clients.append(c);report['connections']=len(clients)
                return Counted(c)
            def snapshot(c, version, name):
                with c.transaction():
                    c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                    caps={**observer.DEFAULT_ROWS,'journal':7}
                    if version=='017':
                        caps.update(relations=224,columns=1830,indexes=416,guards=224)
                    s=observer.observe(c,caps)
                    require(s['groups']['identity'][0]['started_at']==baseline['groups']['identity'][0]['started_at'],
                            'RDS postmaster epoch differs')
                    observer.check_bootstrap(s['groups'])
                    require(not s['groups']['nonbootstrap'],'unexpected typed business rows')
                    shape=overlay.catalogue(c,version)
                    core=overlay.verify_core_defaults(c) if version=='017' else None
                save(out/(name+'.native.json'),s)
                return s,shape,core
            with connect() as writer:
                if args.adopt:
                    for lease in LEASES:
                        require(writer.execute('SELECT pg_try_advisory_lock('+lease+')').fetchone()[0],'existing native lease busy')
                before,shape,_=snapshot(writer,'015','before')
                require(observer.state_hash(before)==STATE,'actual accounted B0 state changed')
                report.update(nativeStateSha256=STATE,beforeCatalogue=shape)
                if not args.adopt:
                    report['status']='verified_readonly_015'
                else:
                    require(shape==prepared['beforeCatalogue'],'approved readonly preflight drift')
                    report['ddlAttempted']=True
                    try:
                        report['transition']=overlay.adopt(writer,shape,release_commit=spec['codeCommit'])
                    except BaseException as error:
                        report['transitionFailure']={'type':type(error).__name__,'sqlstate':getattr(error,'sqlstate',None)}
            if args.adopt:
                with connect() as verifier:
                    version=verifier.execute('SELECT max(version) FROM ingest.schema_migrations').fetchone()[0]
                    require(version in {'015','017'},'unverified migration journal')
                    final,actual,empty=snapshot(verifier,version,'after')
                    if version=='015':
                        require(observer.state_hash(final)==STATE and actual==shape,'rollback state differs')
                        report['status']='rollback_verified_015'
                    else:
                        require(actual['journal'][:4]==shape['journal'] and
                                all(row[3]==spec['codeCommit'] for row in actual['journal'][4:]) and
                                actual['coordinateView']==shape['coordinateView'] and empty['emptyNewTables']==4,
                                'committed adoption does not match exact postcondition')
                        for name in ('bootstrap','sequences','validator','retained'):
                            require(final['groups'][name]==before['groups'][name],'preserved native group differs: '+name)
                        require(not report.get('transition') or report['transition']['after']==actual,'independent catalogue differs')
                        report.update(status='applied_and_independently_verified_017',
                                      afterCatalogue=actual,afterStateSha256=observer.state_hash(final),approvedCoreDefaults=empty)
    except BaseException as error:
        report.update(status='unverified_outcome' if report['ddlAttempted'] else 'refused',errorType=type(error).__name__,
                      sqlstate=getattr(error,'sqlstate',None),reasonCode=getattr(error,'code',None),
                      gate=str(error) if isinstance(error,GateError) else None)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        for c in clients:c.close()
        report.update(connectionsClosed=all(c.closed for c in clients),privateAuthRemoved=private is None or not private.exists(),
                      elapsedSeconds=round(time.monotonic()-started,3))
        if out and out.is_dir():save(out/'result.json',report)
        print(json.dumps({k:report[k] for k in ('status','connections','awsCalls','readStatements','ddlAttempted','elapsedSeconds','connectionsClosed','privateAuthRemoved')}))
    return 0 if report['status'] in {'verified_readonly_015','applied_and_independently_verified_017'} else 1


if __name__=='__main__':raise SystemExit(main())
