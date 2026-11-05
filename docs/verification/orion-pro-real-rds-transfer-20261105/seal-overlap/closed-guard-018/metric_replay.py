"""Owned synthetic COPY cache. No storage, database constructor or provider route."""
from __future__ import annotations
import hashlib
import re

CACHE_MAX=160*1024**2
BLOCK_MAX=1024**2
TABLE='football.player_match_metric_values'
COLS=re.compile(r'"[a-z_][a-z0-9_]*"(?:,"[a-z_][a-z0-9_]*")*')


class ReplayError(ValueError):
    def __init__(self,code):
        super().__init__(code)
        self.code=code


def require(ok,code):
    if not ok:raise ReplayError(code)


class Cache:
    def __init__(self,chunks,evidence):
        self.chunks=tuple(chunks)
        self.evidence=evidence


def capture(conn,batches,*,tick,maximum_bytes=CACHE_MAX):
    require(type(maximum_bytes) is int and 0<maximum_bytes<=CACHE_MAX,'COPY_BUFFER')
    total=rows=peak=0
    digest=hashlib.sha256()
    chunks=[];metadata=[]
    for columns,select,params in batches:
        tick()
        require(COLS.fullmatch(columns) and select.startswith('SELECT '),'COPY_TEMPLATE')
        block=bytearray()
        with conn.cursor().copy('COPY ('+select+') TO STDOUT',params) as output:
            for piece in output:
                future=len(block)+len(piece)
                require(future<=BLOCK_MAX and total+2*future<=maximum_bytes,'COPY_BUFFER')
                block.extend(piece)
        raw=bytes(block);del block
        count=raw.count(b'\n')
        require(0<count<=1000 and raw.endswith(b'\n'),'COPY_ROWS')
        chunk_sha=hashlib.sha256(raw).hexdigest()
        digest.update(str(len(raw)).encode()+b':');digest.update(raw);digest.update(b'\n')
        peak=max(peak,total+2*len(raw));total+=len(raw);rows+=count
        chunks.append((columns,raw,chunk_sha,count))
        metadata.append({'ordinal':len(chunks)-1,'rows':count,'bytes':len(raw),'sha256':chunk_sha})
    require(chunks,'COPY_ROWS')
    return Cache(chunks,{'rows':rows,'commands':len(chunks),'wireBytes':total,'wireSha256':digest.hexdigest(),
                         'peakSyntheticPayloadBytes':peak,'maximumSyntheticPayloadBytes':maximum_bytes,
                         'chunkMetadata':metadata,'rawBodiesPersisted':False})


def replay(conn,cache,*,tick):
    rows=wire=largest=0;digest=hashlib.sha256()
    for columns,raw,expected,count in cache.chunks:
        tick()
        require(hashlib.sha256(raw).hexdigest()==expected and COLS.fullmatch(columns),'COPY_INPUT_DRIFT')
        with conn.cursor().copy('COPY '+TABLE+' ('+columns+') FROM STDIN') as target:
            target.write(raw)
        rows+=count;wire+=len(raw);largest=max(largest,len(raw))
        digest.update(str(len(raw)).encode()+b':');digest.update(raw);digest.update(b'\n')
    combined=digest.hexdigest()
    require(rows==cache.evidence['rows'] and wire==cache.evidence['wireBytes'] and combined==cache.evidence['wireSha256'],
            'COPY_INPUT_DRIFT')
    return {'rows':rows,'commands':len(cache.chunks),'wireBytes':wire,'wireSha256':combined,'largestBlockBytes':largest}
