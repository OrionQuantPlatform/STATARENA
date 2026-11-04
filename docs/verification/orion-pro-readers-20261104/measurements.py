#!/usr/bin/env python3
"""Summarize retained local HTTP evidence; no network, SQL or source reads."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
HEAVY=re.compile(r'\bfootball\.(?:shots|match_heatmaps|match_heatmap_cells|pass_networks|pass_network_nodes|pass_network_edges)\b',re.I)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def kind(path):
    path=urlsplit(path).path
    if path=='/api/dashboard/manifest':return 'manifest'
    if path=='/api/fixtures':return 'fixtures'
    if path.endswith('/summary'):return 'summary'
    return 'shots'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--result',type=Path,required=True);args=p.parse_args()
    source=args.result.resolve();source.relative_to(BASE)
    data=json.loads(source.read_text())
    if data.get('kind')!='owned_pg18_frozen_reader_http_e2e' or data.get('status')!='pass':raise ValueError('Use an actual passing retained reader E2E result')
    components=[];seen=set()
    for request in data['requests']:
        label=(kind(request['path']),request['method'],request['status'])
        if label in seen or request['status'] not in (200,304):continue
        seen.add(label)
        components.append({'requestId':request['id'],'route':label[0],'method':label[1],'status':label[2],
                           'path':request['path'],'logicalJsonBytes':request['bytes'],'sqlStatements':len(request['sql']),
                           'heavyQueries':sum(bool(HEAVY.search(q['sql'] or '')) for q in request['sql']),
                           'httpRoundTripMs':request['elapsedMs'],
                           'clientSqlMs':round(sum(q.get('elapsedMs',0) for q in request['sql']),3)})
    result={'kind':'local_reader_component_observations','atUtc':datetime.now(timezone.utc).isoformat(),
            'command':['python3',str(Path(__file__).relative_to(ROOT)),'--result',str(source.relative_to(ROOT))],
            'input':{'path':str(source.relative_to(ROOT)),'sha256':sha(source)},'analyzerSha256':sha(Path(__file__)),
            'counts':data['counts'],'runtimeIdentity':data['runtimeIdentity'],'requestCount':len(data['requests']),
            'components':components,'comparison':{
                'method':'First successful observation of each route/method/status in scripted order; different workflow components, not paired before/after representations',
                'httpTiming':'Loopback request through complete response body; excludes subsequent diagnostic trace retrieval',
                'bytes':'Logical UTF-8 JSON body bytes, excluding HTTP headers and transport framing',
                'sqlTiming':'pg client query elapsed after a pool lease; no production/RDS comparison',
                'baseline':'Original legacy HTTP RED lacked serving projections and returned errors. It is not a comparable successful baseline.',
                'unverified':['real data/source fidelity','production publisher/collector','Vercel/browser/CDN behavior','remote latency/transfer/storage gains','p95 or causal speedup']}}
    out=source.parent/'measurements.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'output':str(out.relative_to(ROOT)),'sha256':sha(out),'components':components}))


if __name__=='__main__':main()
