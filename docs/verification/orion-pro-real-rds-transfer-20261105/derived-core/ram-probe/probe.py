#!/usr/bin/env python3
"""One exact retained Unix RAM observation. Only aggregates and hashes survive."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time as wall_time, timedelta, timezone
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import re
import resource
import signal
import socket
import stat
import sys
import time
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[4]
PINS = BASE / 'PINS.json'
PINS_SHA = '341cb5f1ca5b7ef03ccf952dc91593543ca2e4e84990332a6135201491abefb3'
SOURCE = Path('/tmp/orion-real-rds-source-20261105-v3/source.sock')
PID = 29953
WIRE = 32 * 1024 ** 2
RSS = 256 * 1024 ** 2
PROOF = 1024 ** 2
SECONDS = 60
CAPTURE_BUDGET = {'selects': 4, 'decodedBytes': 9682314, 'objectHttpRequests': 3, 'physicalHttpBytes': 3961}
TABLES = ('teams', 'players', 'fixtures', 'matches', 'performances')
DIGEST = re.compile('[a-f0-9]{64}')
DAY = re.compile(r'\d{4}-\d{2}-\d{2}', re.ASCII)
CLOCK = r'(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9](?:\.[0-9]{1,6})?)?'
TIME_ONLY = re.compile(CLOCK)
UTC_STAMP = re.compile(r'(\d{4}-\d{2}-\d{2})T(' + CLOCK + r')(Z|\+00:00)', re.ASCII)
MISSING = object()


class Refusal(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(ok, code):
    if not ok:
        raise Refusal(code)


def tick(deadline):
    require(time.monotonic() < deadline, 'DEADLINE')
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss = rss if sys.platform == 'darwin' else rss * 1024
    require(rss <= RSS, 'RSS_BOUND')
    return rss


def digest(path, cap=8 * 1024 ** 2):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_size <= cap, 'PINS')
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def read_metadata(path, expected, cap=8 * 1024 ** 2):
    require(isinstance(expected, str) and DIGEST.fullmatch(expected), 'PINS')
    path = Path(path)
    require(path.is_absolute() and path.resolve().is_relative_to(ROOT), 'PINS')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as file:
        info = os.fstat(file.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= cap, 'PINS')
        raw = file.read(cap+1)
    require(len(raw) <= cap and hashlib.sha256(raw).hexdigest() == expected, 'PINS')
    def unique(items):
        out = {}
        for key, value in items:
            require(key not in out, 'PINS')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(Refusal('PINS')))


def canonical(value):
    if isinstance(value, Decimal):
        require(value.is_finite() and abs(value.adjusted()) <= 1024, 'PACKED_NUMBER')
        return ['number', format(value, 'f')]
    if isinstance(value, dict):
        require(all(isinstance(key, str) for key in value), 'PACKED_SHAPE')
        return ['object', [[k, canonical(v)] for k,v in sorted(value.items())]]
    if isinstance(value, (list,tuple)):
        return ['array', [canonical(v) for v in value]]
    if isinstance(value, datetime):
        return ['timestamp',value.isoformat()]
    require(type(value) in {str,int,bool,type(None),float}, 'PACKED_SCALAR')
    return [type(value).__name__,value]


def canonical_bytes(value):
    return json.dumps(canonical(value),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def hashed(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def framed(h, value):
    body = canonical_bytes(value)
    require(len(body) <= 1024 ** 2, 'PACKED_ROW_BOUND')
    h.update(str(len(body)).encode()+b':'+body+b'\n')


def zone_metadata_getattr(obj, name):
    # ZoneInfo's protocol5 representation uses a getattr reduction.
    # Restrict that reduction to the exact UTC metadata method and values.
    require(obj is ZoneInfo and name == '_unpickle', 'WIRE_CLASS')
    def utc_zone(key, from_cache):
        require(key in {'UTC','Etc/UTC','GMT','Etc/GMT'} and type(from_cache) is int and from_cache in {0,1}, 'WIRE_CLASS')
        return ZoneInfo(key)
    return utc_zone


ALLOWED_CLASSES = {('decimal', 'Decimal'): Decimal, ('datetime', 'datetime'): datetime,
                   ('datetime', 'date'): date, ('datetime', 'timezone'): timezone,
                   ('datetime', 'timedelta'): timedelta, ('datetime', 'time'): wall_time,
                   ('zoneinfo','ZoneInfo'):ZoneInfo,('builtins','getattr'):zone_metadata_getattr}


class SafeUnpickler(pickle._Unpickler):
    def find_class(self, module, name):
        require((module,name) in ALLOWED_CLASSES, 'WIRE_CLASS')
        return ALLOWED_CLASSES[module,name]

    def persistent_load(self, key):
        raise Refusal('WIRE_PERSISTENT')


class WireReader:
    def __init__(self, stream, deadline, maximum_bytes):
        require(type(maximum_bytes) is int and 2 <= maximum_bytes <= WIRE, 'WIRE_BOUND')
        self.stream, self.deadline, self.maximum = stream, deadline, maximum_bytes
        self.count = 0
        self.sha = hashlib.sha256()
        self.prefix = self._read(2)
        require(self.prefix == b'\x80\x05', 'WIRE_FORMAT')

    def _read(self, n):
        tick(self.deadline)
        require(type(n) is int and 0 <= n <= self.maximum-self.count, 'WIRE_BOUND')
        out = self.stream.read(n)
        self.count += len(out)
        self.sha.update(out)
        return out

    def read(self, n):
        prefix, self.prefix = self.prefix[:n], self.prefix[n:]
        return prefix + self._read(n-len(prefix))

    def readline(self):
        out = bytearray()
        for _ in range(65536):
            value = self.read(1)
            if not value or value == b'\n':
                return bytes(out)+value
            out.extend(value)
        raise Refusal('WIRE_FORMAT')


def decode_wire(stream, *, deadline, maximum_bytes=WIRE):
    reader = WireReader(stream,deadline,maximum_bytes)
    unpickler = SafeUnpickler(reader)
    try:
        value = unpickler.load()
    except Refusal:
        raise
    except (ValueError, EOFError, TypeError, IndexError, OverflowError, AttributeError, pickle.UnpicklingError) as error:
        raise Refusal('WIRE_FORMAT') from error
    frame = unpickler._unframer.current_frame
    require((frame is None or not frame.read(1)) and not reader.read(1), 'WIRE_TRAILING')
    require(type(value) is dict, 'WIRE_FORMAT')
    return value, {'wireBytes':reader.count,'wireSha256':reader.sha.hexdigest(),'peakRssBytes':tick(deadline)}


def integer(value, maximum, code='PACKED_SHAPE'):
    require(type(value) in {int,Decimal} and
            (type(value) is int or value.is_finite() and value == value.to_integral_value()) and 0 <= value <= maximum, code)
    return int(value)


def unpack(packed, deadline):
    require(type(packed) is dict and {'keys','rows'} <= set(packed) <= {'keys','rows','dictionaries','missing'}, 'PACKED_SHAPE')
    keys, rows = packed['keys'], packed['rows']
    require(type(keys) is list and 1 <= len(keys) <= 256 and
            all(type(k) is str and 0 < len(k) <= 128 for k in keys) and len(set(keys)) == len(keys) and
            type(rows) is list and len(rows) <= 20000, 'PACKED_SHAPE')
    dictionaries, missing = packed.get('dictionaries',{}), packed.get('missing',{})
    require(type(dictionaries) is type(missing) is dict, 'PACKED_SHAPE')
    for col, words in dictionaries.items():
        require(type(col) is str and col.isascii() and col.isdecimal() and len(col) <= 3 and str(int(col)) == col and int(col) < len(keys) and
                type(words) is list and 0 < len(words) <= len(rows) and
                all(type(w) is str for w in words) and len(set(words)) == len(words), 'PACKED_SHAPE')
    require(all(type(k) is str and k.isascii() and k.isdecimal() and len(k) <= 5 and str(int(k)) == k and
                int(k) < len(rows) and type(v) is list for k,v in missing.items()), 'PACKED_SHAPE')
    for index, row in enumerate(rows):
        if index % 64 == 0:tick(deadline)
        require(type(row) is list and len(row) == len(keys), 'PACKED_SHAPE')
        absent = missing.get(str(index),[])
        missing_cols = {integer(v,len(keys)-1) for v in absent}
        require(len(missing_cols) == len(absent) and all(row[col] is None for col in missing_cols), 'PACKED_SHAPE')
        out = {}
        for col, key in enumerate(keys):
            if col in missing_cols:continue
            value, dictionary = row[col], dictionaries.get(str(col))
            if value is not None and dictionary is not None:
                value = dictionary[integer(value,len(dictionary)-1)]
            out[key] = value
        yield index,out


def identifier(value, prefix, code):
    require(type(value) is str and re.fullmatch(prefix+r'_[A-Za-z0-9]{6}',value), code)
    return value


def label(value, code):
    require(type(value) is str and 0 < len(value.encode()) <= 256 and '\x00' not in value, code)
    return value


def clock_category(raw_day, raw_time):
    if raw_time is MISSING:return 'absent',None
    if raw_time is None:return 'explicit_null',None
    if type(raw_time) is not str:return 'non_string',None
    if not raw_time:return 'empty_string',None
    if type(raw_day) is not str or not DAY.fullmatch(raw_day):return 'date_shape_unqualified',None
    try:
        day = date.fromisoformat(raw_day)
    except ValueError:
        return 'invalid_calendar_date',None
    stamp = UTC_STAMP.fullmatch(raw_time)
    if stamp:
        try:
            instant = datetime.fromisoformat(raw_time.replace('Z','+00:00'))
        except ValueError:
            return 'invalid_utc_timestamp',None
        if instant.date()!=day:return 'utc_date_conflict',None
        precision = 'fraction' if '.' in stamp[2] else 'second' if stamp[2].count(':')==2 else 'minute'
        return 'utc_rfc3339_'+precision,instant
    if TIME_ONLY.fullmatch(raw_time):
        precision = 'fraction' if '.' in raw_time else 'second' if raw_time.count(':')==2 else 'minute'
        return 'utc_time_of_day_'+precision,datetime.combine(day,wall_time.fromisoformat(raw_time),timezone.utc)
    if 'T' in raw_time and re.search(r'[+-][0-9]{2}:[0-9]{2}$',raw_time) and not raw_time.endswith('+00:00'):
        return 'non_utc_offset',None
    if 'T' in raw_time and re.search(r'[0-9]$',raw_time):
        return 'naive_or_unqualified_datetime',None
    return 'unqualified_time_grammar',None


def observe_edition(document, declaration, *, deadline, archive=None, global_profiles=None):
    require(type(document) is dict and document.get('format')=='orion-packed-tables-v1' and
            type(document.get('tables')) is dict and set(TABLES)<=set(document['tables']), 'DOCUMENT_SHAPE')
    fixtures, details, profiles, teams, engagements, performances = {},{},{},set(),{},defaultdict(set)
    all_performance_ids, all_match_players = set(),set()
    digests = {}
    grammar, agreement, coverage = Counter(),Counter(),Counter()
    utc_hash, perf_hash, coverage_hash = hashlib.sha256(),hashlib.sha256(),hashlib.sha256()
    league = declaration['league']
    for name in TABLES:
        packed = document['tables'][name]
        h = hashlib.sha256(b'["array",[')
        count = 0
        for ordinal,row in unpack(packed,deadline):
            count += 1
            body = canonical_bytes(row)
            require(len(body) <= 1024 ** 2, 'PACKED_ROW_BOUND')
            if ordinal:h.update(b',')
            h.update(body)
            if name=='teams':
                tid=identifier(row.get('id'),'t','TEAM_SCOPE')
                require(tid not in teams,'TEAM_SCOPE')
                teams.add(tid)
            elif name=='players':
                pid=identifier(row.get('playerId'),'p','PROFILE_SCOPE')
                ref=label(row.get('id'),'PROFILE_SCOPE')
                require(ref not in profiles,'PROFILE_SCOPE')
                profiles[ref]=pid
            elif name=='fixtures':
                mid=identifier(row.get('id'),'m','FIXTURE_SCOPE')
                require(mid not in fixtures and isinstance(row.get('league'),dict) and row['league'].get('id')==league,'FIXTURE_SCOPE')
                sides=[]
                for side in ('home','away'):
                    item=row.get(side+'_team')
                    require(type(item) is dict,'TEAM_SCOPE')
                    tid=identifier(item.get('id'),'t','TEAM_SCOPE')
                    require(tid in teams,'TEAM_SCOPE')
                    sides.append(tid);engagements.setdefault(tid,(ordinal,side,mid))
                require(sides[0]!=sides[1],'TEAM_SCOPE')
                kind, instant=clock_category(row.get('date',MISSING),row.get('time_utc',MISSING))
                grammar[kind]+=1
                fixtures[mid]=(ordinal,instant,set(sides))
                time_value=row.get('time_utc',MISSING)
                framed(utc_hash,[ordinal,mid,kind,None if time_value is MISSING else time_value,
                                 None if instant is None else instant.isoformat()])
            elif name=='matches':
                mid=identifier(row.get('id'),'m','DETAIL_SCOPE')
                require(mid in fixtures and mid not in details and row.get('leagueId')==league,'DETAIL_SCOPE')
                _, instant=clock_category(row.get('date',MISSING),row.get('timeUtc',MISSING))
                fixture_clock=fixtures[mid][1]
                agreement['unqualified' if instant is None or fixture_clock is None else 'same' if instant==fixture_clock else 'different']+=1
                details[mid]=(ordinal,row.get('detailCollected',MISSING),row.get('players',MISSING),row.get('coverage',MISSING))
            else:
                mid=identifier(row.get('matchId'),'m','PERFORMANCE_SCOPE')
                player=identifier(row.get('playerId'),'p','PERFORMANCE_SCOPE')
                team=identifier(row.get('teamId'),'t','PERFORMANCE_SCOPE')
                pid=label(row.get('id'),'PERFORMANCE_SCOPE')
                pref=label(row.get('playerRef'),'PERFORMANCE_SCOPE')
                resolver = profiles if global_profiles is None else global_profiles
                require(mid in fixtures and team in fixtures[mid][2] and resolver.get(pref)==player and
                        pid not in all_performance_ids and (mid,player) not in all_match_players,'PERFORMANCE_SCOPE')
                all_performance_ids.add(pid);all_match_players.add((mid,player));performances[mid].add(pid)
                framed(perf_hash,[ordinal,mid,player,team,pid,pref])
        h.update(b']]')
        digests[name]=h.hexdigest()
        if archive is not None:
            table=archive['tableInventory'][name]
            require(count==table['rows'] and packed['keys']==table['keys'] and digests[name]==table['decodedRowsSha256'],'ARCHIVED_TABLE_DRIFT')
    for mid,(fixture_ordinal,_,_) in fixtures.items():
        selected=performances[mid]
        if mid not in details:
            status='performance_without_detail' if selected else 'no_detail_observation'
            detail_ordinal=None
        else:
            detail_ordinal,collected,players,flags=details[mid]
            if collected is not True:status='detail_not_confirmed'
            elif type(players) is not list or len(players)>1000 or any(type(x) is not str for x in players):
                status='no_explicit_players_list'
            elif len(set(players))!=len(players) or set(players)!=selected:status='list_mismatch'
            elif not selected:status='explicit_empty_without_endpoint_witness'
            elif type(flags) is not dict or flags.get('players') is not True:status='declared_players_flag_mismatch'
            else:
                try:listed=integer(flags.get('listedPlayers'),1000)
                except Refusal:listed=None
                status='matched_present' if listed==len(selected) else 'declared_players_count_mismatch'
        coverage[status]+=1
        framed(coverage_hash,[fixture_ordinal,detail_ordinal,mid,status,len(selected),hashed(sorted(selected))])
    keyset, detailset=hashed(sorted(fixtures)),hashed(sorted(details))
    if archive is not None:
        require(keyset==archive['fixtureMatchSetSha256'] and detailset==archive['coverageMatchSetSha256'],'ARCHIVED_KEYSET_DRIFT')
    tick(deadline)
    return {'edition':declaration['edition'],'documentSha256':declaration['documentSha256'],
            'counts':{'fixtures':len(fixtures),'details':len(details),'performances':len(all_performance_ids),
                      'listedTeams':len(teams),'editionTeamWitnesses':len(engagements),
                      'fixtureUtcComparable':sum(x[1] is not None for x in fixtures.values()),
                      'completeNonemptyPerformanceObservations':coverage['matched_present']},
            'utcGrammarCounts':dict(grammar),'detailTimeAgreement':dict(agreement),'coverageStates':dict(coverage),
            'witnessDigests':{'decodedTableHashes':digests,'fixtureKeysetSha256':keyset,'detailKeysetSha256':detailset,
                             'fixtureUtcFieldSha256':utc_hash.hexdigest(),'performanceOccurrenceSha256':perf_hash.hexdigest(),
                             'coverageClosureSha256':coverage_hash.hexdigest(),'engagementWitnessSha256':hashed(sorted(engagements.items()))}}


def fixed_inputs(deadline):
    pins=read_metadata(PINS,PINS_SHA,32768)
    require(pins['kind']=='retained_ram_core_metadata_probe_pins_v1' and len(pins['files'])==15 and
            pins['capturePid']==PID and pins['captureSocket']==str(SOURCE) and pins['fullAcceptance'] is False,'PINS')
    for p in pins['files'].values():
        tick(deadline)
        path=ROOT/p['path']
        require(path.resolve().is_relative_to(ROOT) and digest(path)==p['sha256'],'PINS')
    def metadata(key):
        f=pins['files'][key];return read_metadata(ROOT/f['path'],f['sha256'])
    manifest=metadata('manifest')
    receipt=metadata('captureReceipt')
    supervisor=metadata('captureSupervision')
    require(receipt['ready'] is True and receipt['pid']==supervisor['childPid']==PID and receipt['socket']==str(SOURCE) and
            receipt['captureCodeSha256']==pins['files']['captureCode']['sha256'] and
            receipt['normalizerSha256']==manifest['normalizerSha256']==pins['files']['normalizer']['sha256'] and
            receipt['manifestSha256']==pins['files']['manifest']['sha256'] and receipt['budget']==CAPTURE_BUDGET and
            receipt['documentCount']==4 and receipt['rawBodiesPersisted'] is False and supervisor['capture']==receipt and
            supervisor['privateAuthenticationRemoved'] is True,'CAPTURE_RECEIPT')
    return pins,manifest,receipt,metadata


def snapshot_editions(snapshot,manifest,receipt,metadata,deadline):
    keys={'format','captureKind','cache','meta','profile_metadata','profile_gaps','sourceBudget','captureBudget','manifestSha256',
          'normalizerSha256','captureCodeSha256','sourceIdentity','httpReceipt'}
    require(set(snapshot)==keys and snapshot['format']=='orion_source_memory_v1' and
            snapshot['captureKind']==receipt['kind'] and snapshot['captureBudget']==CAPTURE_BUDGET and
            all(snapshot[key]==receipt[key] for key in ('manifestSha256','normalizerSha256','captureCodeSha256','sourceIdentity')),
            'CAPTURE_ENVELOPE')
    expected={x['path']:(x['sha256'],'aws') for x in manifest['aws']['partitions']}
    expected[manifest['aws']['manifest']['path']]=(manifest['aws']['manifest']['physicalSha256'],'aws')
    expected[manifest['neon']['path']]=(manifest['neon']['physicalSha256'],'neon')
    require(set(snapshot['cache'])==set(snapshot['meta'])==set(expected),'DOCUMENT_SCOPE')
    for path,(physical,origin) in expected.items():
        meta=snapshot['meta'][path]
        require(meta['path']==path and meta['physicalSha256']==physical and meta['origin']==origin and
                isinstance(meta['decodedCanonicalSha256'],str) and DIGEST.fullmatch(meta['decodedCanonicalSha256']),'DOCUMENT_SCOPE')
    # The source producer merged profiles across the two exact editions.
    profile_index={}
    for partition in manifest['aws']['partitions']:
        for _,row in unpack(snapshot['cache'][partition['path']]['tables']['players'],deadline):
            ref=label(row.get('id'),'PROFILE_SCOPE')
            pid=identifier(row.get('playerId'),'p','PROFILE_SCOPE')
            require(profile_index.setdefault(ref,pid)==pid,'PROFILE_SCOPE')
    output=[]
    for partition in manifest['aws']['partitions']:
        edition=partition['season']
        require(edition in {'2025/2026','2026/2027'},'DOCUMENT_SCOPE')
        path=partition['path']
        prior=metadata('edition'+edition[:4])
        require(prior['sourcePath']==path and prior['season']==edition and prior['physicalSha256']==partition['sha256'] and
                prior['rawBodyPersisted'] is False and snapshot['meta'][path]['bytes']==partition['bytes'],'DOCUMENT_SCOPE')
        output.append(observe_edition(snapshot['cache'][path],{'edition':edition,'league':partition['leagueId'],
                                      'documentSha256':partition['sha256']},deadline=deadline,archive=prior,
                                      global_profiles=profile_index))
        del prior
    require(len(output)==2 and sum(x['counts']['fixtures'] for x in output)==612 and
            sum(x['counts']['performances'] for x in output)==15437 and sum(x['counts']['details'] for x in output)==387,
            'SOURCE_COUNT')
    return output


def check_socket():
    require(sys.platform=='darwin','PEER_PLATFORM')
    parent,child=SOURCE.parent.lstat(),SOURCE.lstat()
    require(stat.S_ISDIR(parent.st_mode) and stat.S_IMODE(parent.st_mode)==0o700 and
            stat.S_ISSOCK(child.st_mode) and stat.S_IMODE(child.st_mode)==0o600 and parent.st_uid==child.st_uid==os.getuid(),
            'PRIVATE_SOCKET')
    os.kill(PID,0)


def get_wire(deadline,report):
    # Receive to EOF before interpreting bytes. A parser refusal should not
    # close a socket while the frozen server is still sending its snapshot.
    wire=bytearray()
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
        tick(deadline)
        conn.settimeout(min(5,deadline-time.monotonic()))
        conn.connect(str(SOURCE))
        report['socketConnections']=1
        # Darwin sys/un.h: SOL_LOCAL=0, LOCAL_PEERPID=2.
        require(conn.getsockopt(0,2)==PID,'PEER_PID')
        report['peerPidVerified']=True
        report['ramGets']=1
        report['ramGetOutcome']='requested'
        conn.sendall(b'GET\n')
        while True:
            tick(deadline)
            room=WIRE-len(wire)
            require(room>0,'WIRE_BOUND')
            conn.settimeout(min(5,deadline-time.monotonic()))
            block=conn.recv(min(65536,room))
            if not block:break
            wire.extend(block)
    report['ramGetOutcome']='wire_complete'
    report['wireBytes']=len(wire)
    tick(deadline)
    return wire


def live_release(args,pins):
    require(args.release is not None and args.release.is_absolute() and args.release.parent==BASE and args.release_sha256,'RELEASE')
    release=read_metadata(args.release,args.release_sha256,16384)
    expected={'kind':'root_retained_ram_core_metadata_probe_release_v1','approvedBy':'ROOT','probeSha256':digest(__file__),
              'testSha256':pins['files']['test']['sha256'],'protocolSha256':pins['files']['protocol']['sha256'],'pinsSha256':PINS_SHA,
              'captureReceiptSha256':pins['files']['captureReceipt']['sha256'],'capturePid':PID,'captureSocket':str(SOURCE),
              'maximumRamGets':1,'maximumSeconds':SECONDS,'maximumWireBytes':WIRE,'maximumRssBytes':RSS,
              'maximumProofBytes':PROOF,'postgresConnections':0,'providerCalls':0,'businessWrites':0,'fullAcceptance':False}
    require(set(release)==set(expected)|{'expiresAt','allocationId'} and
            canonical_bytes({k:release[k] for k in expected})==canonical_bytes(expected) and
            re.fullmatch('[a-zA-Z0-9-]{1,80}',release['allocationId']),'RELEASE')
    expiry=datetime.fromisoformat(release['expiresAt'])
    require(expiry.tzinfo is not None and datetime.now(timezone.utc)<expiry,'RELEASE')
    return release


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--inventory',action='store_true')
    mode.add_argument('--check-plan',action='store_true')
    parser.add_argument('--release',type=Path)
    parser.add_argument('--release-sha256')
    args=parser.parse_args()
    report={'kind':'retained_ram_core_metadata_observation_v1','status':'offline_plan','connections':0,'socketConnections':0,
            'ramGets':0,'providerCalls':0,'postgresConnections':0,'businessWrites':0,'rawBodiesPersisted':False,
            'matchUtcOrScalarValuesPersisted':False,'businessIdentifiersPersisted':False,'fullAcceptance':False}
    if not (args.inventory or args.check_plan):
        print(json.dumps(report))
        return 0
    run=snapshot=None
    started=time.monotonic();deadline=started+SECONDS
    try:
        if args.inventory:
            require(args.release and args.release_sha256 and not any(k.startswith('PG') for k in os.environ),'RELEASE')
        pins,manifest,receipt,metadata=fixed_inputs(deadline)
        if args.check_plan:
            require(not (args.release or args.release_sha256),'RELEASE')
            report.update(status='verified_retained_metadata_inputs_only',pinsSha256=PINS_SHA,
                          inputFilesVerified=len(pins['files']),noActualSourceObservation=True)
        else:
            release=live_release(args,pins)
            check_socket()
            ledger=BASE/(release['allocationId']+'.consumed.json')
            run=BASE/'observations'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            with ledger.open('x') as file:
                json.dump({'state':'consumed','output':str(run),'releaseSha256':args.release_sha256},file,indent=2);file.write('\n')
            run.mkdir(parents=True,exist_ok=False)
            report.update(command=[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],
                          expected=str(BASE/'PROTOCOL.md'),releaseSha256=args.release_sha256,pinsSha256=PINS_SHA,
                          capturePid=PID,captureReceiptSha256=pins['files']['captureReceipt']['sha256'],
                          probeSha256=digest(__file__),captureBudget=CAPTURE_BUDGET)
            def alarm(signum,frame):raise Refusal('DEADLINE')
            signal.signal(signal.SIGALRM,alarm)
            signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
            wire=get_wire(deadline,report)
            snapshot,meter=decode_wire(io.BytesIO(wire),deadline=deadline)
            require(meter['wireBytes']==len(wire),'WIRE_COUNT')
            del wire
            report.update(wireSha256=meter['wireSha256'],ramGetOutcome='decoded',documentsInSnapshot=4,
                          editions=snapshot_editions(snapshot,manifest,receipt,metadata,deadline))
            os.kill(PID,0)
            require(all(digest(ROOT/p['path'])==p['sha256'] for p in pins['files'].values()),'PINS')
            report.update(status='observed_metadata_only',captureAliveAfter=True,inputsUnchanged=True,peakRssBytes=tick(deadline))
    except BaseException as error:
        report.update(status='fail' if run else 'refused',reasonCode=getattr(error,'code',type(error).__name__))
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        if snapshot is not None:snapshot.clear()
        report['elapsedSeconds']=round(time.monotonic()-started,3)
        body=json.dumps(report,indent=2,ensure_ascii=False).encode()+b'\n'
        require(len(body)<=PROOF-16384,'PROOF_BOUND')
        if run and run.is_dir():(run/'result.json').write_bytes(body)
        print(body.decode(),end='')
    return 0 if report['status'] in {'observed_metadata_only','verified_retained_metadata_inputs_only'} else 1


if __name__=='__main__':raise SystemExit(main())
