#!/usr/bin/env python3
"""Bounded read-only deployment availability E2E; metadata evidence only."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parent
ORIGINS = (
    'https://statarena-analytics.vercel.app',
    'https://orion-football-ranking.vercel.app',
    'https://d317dq37z1tacb.cloudfront.net',
)


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = BASE / 'runs' / stamp
    (run / 'inputs').mkdir(parents=True)
    for name in ('PROTOCOL.md', 'verify_public.py', 'VERCEL_CONTROL.json'):
        shutil.copyfile(BASE / name, run / 'inputs' / name)
    began = time.monotonic()
    report = {'kind': 'public_deployment_readonly_e2e', 'atUtc': stamp,
              'command': 'python3 docs/verification/orion-deployment-readback-20261105/verify_public.py',
              'expected': '6 GET200 JSON, 3 HEAD200 bodyless same ETag, 3 conditional304 bodyless; exact production alias binding',
              'sourceBodiesPersisted': 0, 'mutations': 0, 'fullAcceptance': False,
              'limits': {'requests': 12, 'timeoutSeconds': 10, 'responseBytes': 262144, 'totalBytes': 2097152, 'wallSeconds': 180},
              'cases': [], 'http': [], 'unverified': [], 'errorType': None,
              'suggestedCommit': 'test: verify deployed frontend aliases and public API availability'}
    names = ['control_plane'] + [f'{origin}:{kind}' for origin in ORIGINS for kind in ('health_get', 'manifest_get', 'manifest_head', 'manifest_conditional')]
    consumed = 0
    byte_count = 0
    def request(origin, path, method='GET', etag=None):
        nonlocal consumed, byte_count
        assert consumed < 12 and time.monotonic() - began < 180, 'REQUEST_BUDGET'
        consumed += 1
        headers = {'Accept': 'application/json', 'User-Agent': 'StatArena-deployment-readback/1'}
        if etag is not None:
            headers['If-None-Match'] = etag
        req = urllib.request.Request(origin + path, headers=headers, method=method)
        t0 = time.monotonic()
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(262145)
            byte_count += len(body)
            entry = {'url': origin + path, 'method': method, 'conditional': etag is not None,
                     'status': response.status, 'bytes': len(body), 'bodySha256': hashlib.sha256(body).hexdigest(),
                     'roundTripMs': round((time.monotonic() - t0) * 1000, 3),
                     'headers': {k: response.headers.get(k) for k in ('ETag', 'Cache-Control', 'Content-Type', 'Age', 'X-Cache', 'X-Vercel-Cache', 'Server-Timing')},
                     'sameOrigin': urllib.parse.urlsplit(response.url).netloc == urllib.parse.urlsplit(origin).netloc}
        report['http'].append(entry)
        assert len(body) <= 262144 and byte_count <= 2097152 and entry['sameOrigin'], 'BODY_OR_ORIGIN_BOUND'
        return entry, body
    current = 'control_plane'
    try:
        control = json.loads((BASE / 'VERCEL_CONTROL.json').read_text())
        d = control['deployment']
        assert control['passed'] and d['id'] == control['expected']['id'] and d['sourceCommit'] == control['expected']['sourceCommit'] and d['state'] == 'READY' and d['target'] == 'production'
        assert len(control['aliases']) == 2 and all(a['deploymentId'] == d['id'] and a['projectId'] == control['expected']['projectId'] for a in control['aliases'])
        report['cases'].append({'case': current, 'status': 'pass'})
        for origin in ORIGINS:
            for path, kind in (('/api/health', 'health_get'), ('/api/dashboard/manifest', 'manifest_get')):
                current = f'{origin}:{kind}'
                entry, body = request(origin, path)
                assert entry['status'] == 200 and 'json' in (entry['headers']['Content-Type'] or '').lower(), 'GET_STATUS_OR_TYPE'
                value = json.loads(body)
                assert isinstance(value, dict) and value, 'JSON_OBJECT'
                entry['jsonKeys'] = sorted(value)
                report['cases'].append({'case': current, 'status': 'pass'})
                if kind == 'manifest_get':
                    manifest_etag = entry['headers']['ETag']
                    assert isinstance(manifest_etag, str) and manifest_etag, 'MANIFEST_ETAG'
            current = f'{origin}:manifest_head'
            entry, body = request(origin, '/api/dashboard/manifest', method='HEAD')
            assert entry['status'] == 200 and not body and entry['headers']['ETag'] == manifest_etag, 'HEAD_STATUS_BODY_ETAG'
            report['cases'].append({'case': current, 'status': 'pass'})
            current = f'{origin}:manifest_conditional'
            entry, body = request(origin, '/api/dashboard/manifest', etag=manifest_etag)
            assert entry['status'] == 304 and not body, 'CONDITIONAL_STATUS_BODY'
            report['cases'].append({'case': current, 'status': 'pass'})
    except Exception as error:
        report['cases'].append({'case': current, 'status': 'fail'})
        report['errorType'] = type(error).__name__
        if isinstance(error, AssertionError):
            report['assertion'] = str(error)
    done = {c['case'] for c in report['cases']}
    report['unverified'] = [name for name in names if name not in done]
    report['counts'] = {'pass': sum(c['status'] == 'pass' for c in report['cases']),
                        'fail': sum(c['status'] == 'fail' for c in report['cases']), 'unverified': len(report['unverified'])}
    report['status'] = 'pass' if report['counts'] == {'pass': 13, 'fail': 0, 'unverified': 0} else 'fail'
    report['consumedRequests'] = consumed
    report['receivedBytes'] = byte_count
    report['elapsedSeconds'] = round(time.monotonic() - began, 3)
    report['inputSha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (run / 'inputs').iterdir()}
    (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'requests': consumed, 'receivedBytes': byte_count, 'result': str(run / 'result.json')}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
