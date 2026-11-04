#!/usr/bin/env python3
"""Live, reversible E2E comparison; captures only public data and safe AWS fields."""
import datetime, gzip, hashlib, http.client, json, pathlib, re, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parent
AWS = ['aws', '--profile', 'statarena', '--region', 'us-east-2']
FUNCTION = 'statarena-backend'
HOST = 'd317dq37z1tacb.cloudfront.net'
PATH = '/api/seasons/partition?season=2026%2F2027&league=l_0ALvwF&limit=100&format=columns'
SHA = '0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403'
EXPECTED_CODE = 'F8nND1oBu4BU7+CuB6n5+SUiQ5J706zW+qZZG88np1c='
OUT = ROOT / 'result.json'
report = {'started': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'rerun': 'python3 docs/verification/aws-lambda-memory-20261104/compare.py',
          'url': 'https://' + HOST + PATH, 'expected': {'sha256': SHA, 'decodedBytes': 1973314,
          'encodedBytes': 431391, 'status': 200, 'cache': 'no-store'}, 'configurations': [],
          'passed': False, 'restored': False}

def save():
    OUT.write_text(json.dumps(report, indent=2) + '\n')

def aws(*args):
    p = subprocess.run(AWS + list(args) + ['--output', 'json'], check=True, capture_output=True, text=True)
    return json.loads(p.stdout)

def config():
    return aws('lambda', 'get-function-configuration', '--function-name', FUNCTION,
               '--query', '{MemorySize:MemorySize,State:State,LastUpdateStatus:LastUpdateStatus,CodeSha256:CodeSha256}')

def set_memory(value):
    before = config()
    assert before['CodeSha256'] == EXPECTED_CODE, 'Code changed during comparison'
    result = aws('lambda', 'update-function-configuration', '--function-name', FUNCTION,
                 '--memory-size', str(value), '--query', '{MemorySize:MemorySize,State:State,LastUpdateStatus:LastUpdateStatus}')
    for _ in range(90):
        state = config()
        if state['LastUpdateStatus'] == 'Successful' and state['State'] == 'Active':
            assert state['MemorySize'] == value
            return {'requested': result, 'ready': state}
        assert state['LastUpdateStatus'] != 'Failed', 'Memory update failed'
        time.sleep(1)
    raise TimeoutError('Lambda configuration not ready')

def samples(value):
    section = {'memoryMiB': value, 'config': config(), 'startMs': int(time.time()*1000), 'rows': []}
    report['configurations'].append(section); save()
    connection = http.client.HTTPSConnection(HOST, timeout=45)
    try:
        for index in range(6):
            start_ms = int(time.time()*1000)
            start = time.perf_counter()
            connection.request('GET', PATH, headers={'Accept-Encoding': 'gzip', 'User-Agent': 'StatArena-memory-E2E/1'})
            response = connection.getresponse()
            wire = response.read()
            elapsed = (time.perf_counter() - start) * 1000
            encoding = response.getheader('Content-Encoding')
            body = gzip.decompress(wire) if encoding == 'gzip' else wire
            row = {'index': index, 'firstAfterConfiguration': index == 0, 'startMs': start_ms,
                   'endMs': int(time.time()*1000), 'elapsedMs': round(elapsed, 2),
                   'status': response.status, 'encodedBytes': len(wire), 'decodedBytes': len(body),
                   'sha256': hashlib.sha256(body).hexdigest(), 'encoding': encoding,
                   'cache': response.getheader('Cache-Control'), 'edgeCache': response.getheader('X-Cache'),
                   'etag': response.getheader('ETag'), 'pop': response.getheader('X-Amz-Cf-Pop'),
                   'originRequestId': response.getheader('X-Amzn-Requestid')}
            section['rows'].append(row); save()
            assert row['status'] == 200 and row['sha256'] == SHA and row['decodedBytes'] == 1973314
            assert row['encodedBytes'] == 431391 and row['cache'] == 'no-store' and encoding == 'gzip'
            assert row['edgeCache'] == 'Miss from cloudfront'
            print(json.dumps({'memoryMiB': value, **row}), flush=True)
    finally:
        connection.close()
        section['endMs'] = int(time.time()*1000); save()

def logs():
    start = min(c['startMs'] for c in report['configurations']) - 2000
    end = max(c['endMs'] for c in report['configurations']) + 10000
    streams = aws('logs', 'describe-log-streams', '--log-group-name', '/aws/lambda/' + FUNCTION,
                  '--order-by', 'LastEventTime', '--descending', '--limit', '8').get('logStreams', [])
    events = []
    for stream in streams:
        if stream.get('lastEventTimestamp', 0) < start: continue
        data = aws('logs', 'get-log-events', '--log-group-name', '/aws/lambda/' + FUNCTION,
                   '--log-stream-name', stream['logStreamName'], '--start-time', str(start), '--end-time', str(end))
        for event in data.get('events', []):
            message = event.get('message', '')
            if message.startswith('REPORT RequestId:'):
                events.append({'timestamp': event['timestamp'], 'stream': stream['logStreamName'], 'message': message.strip()})
    return events

try:
    assert aws('sts', 'get-caller-identity', '--query', 'Account') == '361769570630', 'Wrong account'
    report['original'] = config(); save()
    assert report['original']['MemorySize'] == 512 and report['original']['LastUpdateStatus'] == 'Successful'
    assert report['original']['CodeSha256'] == EXPECTED_CODE
    report['update1024'] = set_memory(1024); save()
    samples(1024)
    report['restore512'] = set_memory(512); report['restored'] = True; save()
    samples(512)
    time.sleep(4)
    report['lambdaReports'] = logs()
    report['passed'] = True
except BaseException as error:
    report['error'] = type(error).__name__ + ': ' + str(error)
    raise
finally:
    if report.get('original', {}).get('MemorySize') == 512 and config()['MemorySize'] != 512:
        report['restore512'] = set_memory(512)
        report['restored'] = True
    report['final'] = config(); report['finished'] = datetime.datetime.now(datetime.timezone.utc).isoformat(); save()
    print(json.dumps({'receipt': str(OUT), 'passed': report['passed'], 'restored': report['restored'], 'final': report['final']}), flush=True)
