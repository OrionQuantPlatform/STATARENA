#!/usr/bin/env python3
"""Symbolic protocol5 global-name inspection; never unpickles any object."""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pickletools
import re
import signal
import sys
import time

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[5]
PINS=BASE/'PINS.json'
PINS_SHA='8526671990a828e178aa32e319e7464735fefab54ccf6df589fc2d02bf7077ba'
spec=importlib.util.spec_from_file_location('frozen_ram_v2_frame_auditor',BASE.parent/'v2/probe_v2.py')
v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)
v1=v2.v1
require=v1.require
OTHER,MARK=-1,-2
ASCII_SYMBOL=re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')


def identifier_token(buffer,offset):
    require(type(offset) is int and 0<=offset<len(buffer),'GLOBAL_SYMBOL')
    widths={0x8c:1,0x58:4,0x8d:8}  # SHORT_BINUNICODE, BINUNICODE, BINUNICODE8
    width=widths.get(buffer[offset]);require(width is not None,'GLOBAL_SYMBOL')
    start=offset+1+width
    size=int.from_bytes(buffer[offset+1:start],'little')
    require(0<size<=128 and start+size<=len(buffer),'GLOBAL_SYMBOL')
    try:text=bytes(buffer[start:start+size]).decode('ascii')
    except UnicodeError as error:raise v1.Refusal('GLOBAL_SYMBOL') from error
    require(ASCII_SYMBOL.fullmatch(text),'GLOBAL_SYMBOL')
    return text


def inventory_symbols(buffer,*,deadline):
    require(type(buffer) in {bytes,bytearray} and 2<=len(buffer)<v2.WIRE and buffer[:2]==b'\x80\x05','WIRE_BOUND')
    frames=v2.audit_pickle(buffer,deadline)
    stack=[]
    memo=array('i');require(memo.itemsize==4,'DIAGNOSTIC_PLATFORM')
    seen=Counter()
    view=v2.BufferView(buffer,deadline)
    operations=reductions=peak_stack=0
    def add(module,name):
        require(len(module)<=128 and len(name)<=128 and ASCII_SYMBOL.fullmatch(module) and ASCII_SYMBOL.fullmatch(name),
                'GLOBAL_SYMBOL')
        require((module,name) in seen or len(seen)<16,'GLOBAL_SYMBOL_BOUND')
        seen[(module,name)]+=1
    try:
        for op,arg,offset in pickletools.genops(view):
            operations+=1
            if operations%4096==0:v1.tick(deadline)
            tag=op.name
            if tag in {'SHORT_BINUNICODE','BINUNICODE','BINUNICODE8'}:
                # Retain only a byte offset. Non-global text is never retained.
                stack.append(offset)
            elif tag=='STACK_GLOBAL':
                require(len(stack)>=2 and stack[-1]>=0 and stack[-2]>=0,'GLOBAL_SYMBOL')
                name=identifier_token(buffer,stack.pop());module=identifier_token(buffer,stack.pop());add(module,name)
                stack.append(OTHER)
            elif tag=='GLOBAL':
                tokens=arg.split(' ');require(len(tokens)==2,'GLOBAL_SYMBOL')
                add(*tokens);stack.append(OTHER)
            elif tag=='MEMOIZE':
                require(stack and stack[-1]!=MARK,'WIRE_FORMAT')
                memo.append(stack[-1])
            elif tag in {'BINGET','LONG_BINGET','GET'}:
                require(type(arg) is int and 0<=arg<len(memo),'WIRE_FORMAT');stack.append(memo[arg])
            elif tag=='MARK':
                stack.append(MARK)
            elif tag=='DUP':
                require(stack and stack[-1]!=MARK,'WIRE_FORMAT');stack.append(stack[-1])
            elif pickletools.markobject in op.stack_before:
                require(tag in {'APPENDS','SETITEMS','ADDITEMS','LIST','TUPLE','DICT','FROZENSET','POP_MARK'},'WIRE_OPCODE')
                mark=len(stack)-1
                while mark>=0 and stack[mark]!=MARK:mark-=1
                require(mark>=0,'WIRE_FORMAT');del stack[mark:]
                if tag in {'LIST','TUPLE','DICT','FROZENSET'}:stack.append(OTHER)
                elif tag!='POP_MARK':require(stack and stack[-1]!=MARK,'WIRE_FORMAT')
            else:
                consume=len(op.stack_before)
                require(len(stack)>=consume and (not consume or MARK not in stack[-consume:]),'WIRE_FORMAT')
                if consume:del stack[-consume:]
                stack.extend([OTHER]*len(op.stack_after))
            if tag in {'REDUCE','NEWOBJ','NEWOBJ_EX','BUILD'}:reductions+=1
            peak_stack=max(peak_stack,len(stack))
            require(peak_stack<=65536 and len(memo)<=len(buffer),'SYMBOL_STACK_BOUND')
        require(operations==frames['pickleOpcodes'] and not stack and view.tell()==len(buffer),'WIRE_FORMAT')
    finally:view.close()
    globals_seen=[{'module':module,'name':name,'globalOpcodes':n,'allowedInV2':(module,name) in v1.ALLOWED_CLASSES}
                  for (module,name),n in sorted(seen.items())]
    return {'globals':globals_seen,'unknownGlobalCount':sum(not x['allowedInV2'] for x in globals_seen),
            'globalNameCount':len(globals_seen),'reductionsEncountered':reductions,'reductionsExecuted':0,
            'dataDecoded':False,'wireBytes':len(buffer),'wireSha256':hashlib.sha256(buffer).hexdigest(),
            'pickleFrames':frames['pickleFrames'],'pickleOpcodes':operations,'memoSlots':len(memo),
            'peakStackSlots':peak_stack,'peakRssBytes':v1.tick(deadline),'argumentsExamined':False}


def inputs(deadline):
    pins=v1.read_metadata(PINS,PINS_SHA,32768)
    require(pins['kind']=='retained_ram_symbol_diagnostic_pins_v1' and pins['fullAcceptance'] is False,'PINS')
    for p in pins['files'].values():
        v1.tick(deadline);require(v1.digest(ROOT/p['path'])==p['sha256'],'PINS')
    prior=pins['files']['failedV2']
    fail=v1.read_metadata(ROOT/prior['path'],prior['sha256'],32768)
    require(fail['status']=='fail' and fail['reasonCode']=='WIRE_CLASS' and fail['ramGets']==1 and
            fail['wireBytes']==pins['previousActualWireBytes']==v2.ACTUAL_V1_WIRE and
            fail['observedPeakRssBytes']==pins['previousActualPeakRssBytes']>v2.RSS,'PINS')
    old,_,receipt,_=v1.fixed_inputs(deadline)
    return pins,old,receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--check-plan',action='store_true');mode.add_argument('--diagnose',action='store_true')
    parser.add_argument('--release',type=Path);parser.add_argument('--release-sha256')
    args=parser.parse_args();started=time.monotonic();deadline=started+v2.SECONDS
    report={'kind':'retained_ram_global_symbols_diagnostic_v1','status':'offline_plan','sourceCalls':0,'ramGets':0,'socketConnections':0,
            'providerCalls':0,'postgresConnections':0,'businessWrites':0,'rawBodiesPersisted':False,'reductionsExecuted':0,
            'dataDecoded':False,'fullAcceptance':False}
    if not(args.check_plan or args.diagnose):print(json.dumps(report));return 0
    run=None
    try:
        if args.diagnose:
            require(args.release and args.release.is_absolute() and args.release.parent==BASE and args.release_sha256 and
                    not any(k.startswith('PG') for k in os.environ),'RELEASE')
        pins,old,_=inputs(deadline)
        if args.check_plan:
            require(not(args.release or args.release_sha256),'RELEASE')
            report.update(status='verified_diagnostic_metadata_only',pinsSha256=PINS_SHA)
        else:
            released=v1.read_metadata(args.release,args.release_sha256,16384)
            expected={'kind':'root_retained_ram_global_symbol_diagnostic_v1','approvedBy':'ROOT','diagnosticSha256':v1.digest(__file__),
                      'testSha256':pins['files']['test']['sha256'],'protocolSha256':pins['files']['protocol']['sha256'],
                      'pinsSha256':PINS_SHA,'captureReceiptSha256':old['files']['captureReceipt']['sha256'],'capturePid':v1.PID,
                      'captureSocket':str(v1.SOURCE),'failedV2Sha256':pins['files']['failedV2']['sha256'],'maximumRamGets':1,
                      'maximumSeconds':v2.SECONDS,'maximumWireBytes':v2.WIRE,'maximumRssBytes':v2.RSS,'maximumProofBytes':v2.PROOF,
                      'reductionsExecuted':0,'postgresConnections':0,'providerCalls':0,'businessWrites':0,'fullAcceptance':False}
            require(set(released)==set(expected)|{'allocationId','expiresAt'} and
                    v1.canonical_bytes({k:released[k] for k in expected})==v1.canonical_bytes(expected) and
                    re.fullmatch('[a-zA-Z0-9-]{1,80}',released['allocationId']),'RELEASE')
            expiry=datetime.fromisoformat(released['expiresAt'])
            require(expiry.tzinfo is not None and datetime.now(timezone.utc)<expiry,'RELEASE')
            v1.check_socket()
            proposed=BASE/'observations'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            with (BASE/(released['allocationId']+'.consumed.json')).open('x') as ledger:
                json.dump({'state':'consumed','output':str(proposed),'releaseSha256':args.release_sha256},ledger)
            run=proposed;run.mkdir(parents=True,exist_ok=False)
            report.update(command=[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],
                          expected=str(BASE/'PROTOCOL.md'),releaseSha256=args.release_sha256,pinsSha256=PINS_SHA)
            def stop(signum,frame):raise v1.Refusal('DEADLINE')
            signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
            wire=v1.get_wire(deadline,report);require(len(wire)==v2.ACTUAL_V1_WIRE,'WIRE_SIZE_DRIFT')
            report['sourceCalls']=report['ramGets']
            symbols=inventory_symbols(wire,deadline=deadline);del wire
            os.kill(v1.PID,0)
            require(all(v1.digest(ROOT/p['path'])==p['sha256'] for p in [*pins['files'].values(),*old['files'].values()]),'PINS')
            report.update(status='technical_symbols_observed',technicalSymbols=symbols,captureAliveAfter=True,inputsUnchanged=True)
    except BaseException as error:
        report.update(status='fail' if run else 'refused',reasonCode=getattr(error,'code',type(error).__name__))
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        report['elapsedSeconds']=round(time.monotonic()-started,3)
        text=json.dumps(report,indent=2,ensure_ascii=True)+'\n';require(len(text.encode())<=v2.PROOF-16384,'PROOF_BOUND')
        if run and run.is_dir():(run/'result.json').write_text(text)
        print(text,end='')
    return 0 if report['status'] in {'technical_symbols_observed','verified_diagnostic_metadata_only'} else 1

if __name__=='__main__':raise SystemExit(main())
