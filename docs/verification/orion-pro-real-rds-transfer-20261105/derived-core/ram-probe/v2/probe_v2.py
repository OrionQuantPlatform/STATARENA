#!/usr/bin/env python3
"""V2 candidate: one retained RAM read with bounded, restricted C decoding."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pickle
import pickletools
import resource
import re
import signal
import sys
import time

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[5]
PINS=BASE/'PINS.json'
PINS_SHA='54de14c8276760b41d6fc882fa2fb13bcfd6a3700e98b1a522456f004fe559fb'
ARCHIVES=BASE/'ARCHIVES.json'
ACTUAL_V1_WIRE=12208712
V1=BASE.parent/'probe.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


v1=load(V1,'frozen_retained_ram_probe_v1')
WIRE,RSS,PROOF,SECONDS=v1.WIRE,v1.RSS,v1.PROOF,v1.SECONDS
require=v1.require


class BufferView:
    """Independent seek-free cursors over one bytes buffer; only item reads copy."""
    def __init__(self,body,deadline):
        self.data=memoryview(body).toreadonly()
        self.pos=0
        self.deadline=deadline
        self.next_check=0

    def tell(self):
        return self.pos

    def take(self,n):
        require(type(n) is int and 0<=n<=1024**2,'WIRE_ITEM_BOUND')
        if self.pos>=self.next_check:
            v1.tick(self.deadline)
            self.next_check=self.pos+256*1024
        end=min(self.pos+n,len(self.data))
        piece=self.data[self.pos:end]
        self.pos=end
        return piece

    def read(self,n):
        return self.take(n).tobytes()

    def readinto(self,buffer):
        value=self.take(len(buffer))
        memoryview(buffer)[:len(value)]=value
        return len(value)

    def readline(self):
        remaining=self.data[self.pos:min(self.pos+65536,len(self.data))].tobytes()
        index=remaining.find(b'\n')
        require(index>=0,'WIRE_FORMAT')
        return self.read(index+1)

    def close(self):
        self.data.release()


class SafeDecoder(pickle.Unpickler):
    def find_class(self,module,name):
        require((module,name) in v1.ALLOWED_CLASSES,'WIRE_CLASS')
        return v1.ALLOWED_CLASSES[module,name]

    def persistent_load(self,key):
        raise v1.Refusal('WIRE_PERSISTENT')


def receive_buffer(read,deadline):
    body=bytearray()
    while True:
        v1.tick(deadline)
        room=WIRE-len(body)
        require(room>0,'WIRE_BOUND')
        block=read(min(room,65536))
        if not block:return body
        body.extend(block)


def audit_pickle(buffer,deadline):
    view=BufferView(buffer,deadline)
    frame_end=None
    frames=ops=0
    final_stop=False
    disabled={'NEXT_BUFFER','READONLY_BUFFER','EXT1','EXT2','EXT4','PERSID','BINPERSID','PUT','BINPUT','LONG_BINPUT'}
    try:
        for op,arg,offset in pickletools.genops(view):
            ops+=1
            if ops%4096==0:v1.tick(deadline)
            at=view.tell()
            if frame_end is not None:
                require(offset<=frame_end,'WIRE_FORMAT')
                if offset==frame_end:frame_end=None
                else:require(at<=frame_end,'WIRE_FORMAT')
            require(op.name not in disabled,'WIRE_OPCODE')
            if op.name=='PROTO':require(offset==0 and arg==5,'WIRE_FORMAT')
            if op.name=='FRAME':
                require(frame_end is None and type(arg) is int and 0<arg<=1024**2 and at+arg<=len(buffer),'WIRE_FORMAT')
                frame_end=at+arg
                frames+=1
            if op.name=='STOP':
                require(at==len(buffer) and (frame_end is None or frame_end==at),'WIRE_TRAILING')
                final_stop=True
        require(final_stop,'WIRE_FORMAT')
        return {'pickleFrames':frames,'pickleOpcodes':ops}
    except v1.Refusal:
        raise
    except (ValueError,EOFError,TypeError,OverflowError) as error:
        raise v1.Refusal('WIRE_FORMAT') from error
    finally:
        view.close()


def decode_buffer(buffer,*,deadline,maximum_bytes=WIRE):
    require(type(buffer) in {bytearray,bytes} and type(maximum_bytes) is int and
            2<=len(buffer)<=maximum_bytes<=WIRE,'WIRE_BOUND')
    require(buffer[:2]==b'\x80\x05','WIRE_FORMAT')
    before=v1.tick(deadline)
    inspection=audit_pickle(buffer,deadline)
    prescan=v1.tick(deadline)
    view=BufferView(buffer,deadline)
    decoder=SafeDecoder(view,fix_imports=False)
    try:
        value=decoder.load()
        require(view.tell()==len(buffer) and type(value) is dict,'WIRE_FORMAT')
        decoder.memo.clear()
    except v1.Refusal:
        raise
    except (ValueError,EOFError,TypeError,OverflowError,AttributeError,pickle.UnpicklingError) as error:
        raise v1.Refusal('WIRE_FORMAT') from error
    finally:
        del decoder
        view.close()
    return value,{'wireBytes':len(buffer),'wireSha256':hashlib.sha256(buffer).hexdigest(),**inspection,
                  'beforeDecodePeakRssBytes':before,'afterFrameAuditPeakRssBytes':prescan,
                  'afterDecodePeakRssBytes':v1.tick(deadline),'fullWireCopiesCreated':0}


def projected_archive(original):
    row={k:original[k] for k in ('sourcePath','season','physicalSha256','rawBodyPersisted',
                                 'fixtureMatchSetSha256','coverageMatchSetSha256')}
    row['tableInventory']={name:{key:original['tableInventory'][name][key] for key in ('rows','keys','decodedRowsSha256')}
                           for name in v1.TABLES}
    return row


def inputs(deadline):
    pins=v1.read_metadata(PINS,PINS_SHA,32768)
    require(pins['kind']=='retained_ram_core_metadata_probe_v2_pins' and pins['fullAcceptance'] is False and
            pins['wireBytesPreviouslyObserved']==ACTUAL_V1_WIRE and len(pins['files'])==10,'PINS')
    for record in pins['files'].values():
        v1.tick(deadline)
        require(v1.digest(ROOT/record['path'])==record['sha256'],'PINS')
    failure=pins['files']['realV1Failure']
    prior=v1.read_metadata(ROOT/failure['path'],failure['sha256'],32768)
    require(prior['status']=='fail' and prior['reasonCode']=='RSS_BOUND' and prior['ramGets']==1 and
            prior['wireBytes']==ACTUAL_V1_WIRE and prior['ramGetOutcome']=='wire_complete' and 'editions' not in prior,'PINS')
    old,manifest,receipt,metadata=v1.fixed_inputs(deadline)
    small=v1.read_metadata(ARCHIVES,pins['files']['archives']['sha256'],65536)
    require(small['kind']=='projected_immutable_ram_source_metadata_v2' and small['rawBodiesPersisted'] is False and
            set(small['editions'])=={'edition2025','edition2026'},'PINS')
    for key in small['editions']:
        require(projected_archive(metadata(key))==small['editions'][key],'PINS')
    require(old['files']['captureReceipt']['sha256']==pins['preservedCaptureReceiptSha256'],'PINS')
    v1.tick(deadline)
    return pins,old,manifest,receipt,small['editions']


def release_metadata(args,pins,old):
    require(args.release and args.release.is_absolute() and args.release.parent==BASE and args.release_sha256,'RELEASE')
    data=v1.read_metadata(args.release,args.release_sha256,16384)
    expected={'kind':'root_retained_ram_core_metadata_probe_release_v2','approvedBy':'ROOT',
              'probeSha256':v1.digest(__file__),'testSha256':pins['files']['test']['sha256'],
              'protocolSha256':pins['files']['protocol']['sha256'],'pinsSha256':PINS_SHA,
              'captureReceiptSha256':old['files']['captureReceipt']['sha256'],'capturePid':v1.PID,'captureSocket':str(v1.SOURCE),
              'retainedFailedV1ReceiptSha256':pins['files']['realV1Failure']['sha256'],'maximumRamGets':1,'maximumSeconds':SECONDS,
              'maximumWireBytes':WIRE,'maximumRssBytes':RSS,'maximumProofBytes':PROOF,'postgresConnections':0,'providerCalls':0,
              'businessWrites':0,'fullAcceptance':False}
    require(set(data)==set(expected)|{'expiresAt','allocationId'} and
            v1.canonical_bytes({k:data[k] for k in expected})==v1.canonical_bytes(expected) and
            re.fullmatch('[a-zA-Z0-9-]{1,80}',data['allocationId']),'RELEASE')
    expiry=datetime.fromisoformat(data['expiresAt'])
    require(expiry.tzinfo is not None and datetime.now(timezone.utc)<expiry,'RELEASE')
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--check-plan',action='store_true')
    mode.add_argument('--inventory',action='store_true')
    p.add_argument('--release',type=Path)
    p.add_argument('--release-sha256')
    args=p.parse_args()
    started=time.monotonic()
    deadline=started+SECONDS
    report={'kind':'retained_ram_core_metadata_observation_v2','status':'offline_plan','ramGets':0,'socketConnections':0,
            'postgresConnections':0,'providerCalls':0,'businessWrites':0,'rawBodiesPersisted':False,
            'matchUtcOrScalarValuesPersisted':False,'businessIdentifiersPersisted':False,'fullAcceptance':False}
    if not (args.check_plan or args.inventory):
        print(json.dumps(report))
        return 0
    run=snapshot=None
    stage='pins'
    try:
        if args.inventory:
            require(args.release and args.release_sha256 and not any(k.startswith('PG') for k in os.environ),'RELEASE')
        pins,old,manifest,receipt,archives=inputs(deadline)
        if args.check_plan:
            require(not(args.release or args.release_sha256),'RELEASE')
            report.update(status='verified_retained_metadata_inputs_only',pinsSha256=PINS_SHA,
                          archiveManifestBytes=ARCHIVES.stat().st_size,originalInputPinsVerified=len(old['files']),
                          v2InputPinsVerified=len(pins['files']),previousWireBytes=ACTUAL_V1_WIRE,noActualSourceObservation=True)
        else:
            stage='release'
            release=release_metadata(args,pins,old)
            v1.check_socket()
            proposed=BASE/'observations'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            with (BASE/(release['allocationId']+'.consumed.json')).open('x') as ledger:
                json.dump({'state':'consumed','output':str(proposed),'releaseSha256':args.release_sha256},ledger,indent=2)
                ledger.write('\n')
            run=proposed
            run.mkdir(parents=True,exist_ok=False)
            report.update(command=[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],
                          expected=str(BASE/'PROTOCOL.md'),probeSha256=v1.digest(__file__),pinsSha256=PINS_SHA,
                          releaseSha256=args.release_sha256,failedV1ReceiptSha256=pins['files']['realV1Failure']['sha256'],
                          captureReceiptSha256=old['files']['captureReceipt']['sha256'],capturePid=v1.PID)
            def alarm(signum,frame):raise v1.Refusal('DEADLINE')
            signal.signal(signal.SIGALRM,alarm)
            signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
            stage='receive'
            wire=v1.get_wire(deadline,report)
            require(len(wire)==ACTUAL_V1_WIRE,'WIRE_SIZE_DRIFT')
            stage='restricted_decode'
            snapshot,meter=decode_buffer(wire,deadline=deadline)
            del wire
            report.update(wireMeter=meter,ramGetOutcome='decoded')
            stage='streaming_row_inventory'
            report['editions']=v1.snapshot_editions(snapshot,manifest,receipt,lambda k:archives[k],deadline)
            os.kill(v1.PID,0)
            require(all(v1.digest(ROOT/f['path'])==f['sha256'] for f in [*old['files'].values(),*pins['files'].values()]),'PINS')
            report.update(status='observed_metadata_only',inputsUnchanged=True,captureAliveAfter=True,
                          afterTraversalPeakRssBytes=v1.tick(deadline),documentsInSnapshot=4)
    except BaseException as error:
        report.update(status='fail' if run else 'refused',failedStage=stage,reasonCode=getattr(error,'code',type(error).__name__))
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        if snapshot is not None:snapshot.clear()
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report.update(elapsedSeconds=round(time.monotonic()-started,3),
                      observedPeakRssBytes=rss if sys.platform=='darwin' else rss*1024)
        body=json.dumps(report,indent=2,ensure_ascii=False).encode()+b'\n'
        require(len(body)<=PROOF-16384,'PROOF_BOUND')
        if run and run.is_dir():(run/'result.json').write_bytes(body)
        print(body.decode(),end='')
    return 0 if report['status'] in {'observed_metadata_only','verified_retained_metadata_inputs_only'} else 1


if __name__=='__main__':raise SystemExit(main())
