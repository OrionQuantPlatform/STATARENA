"""Exact-key content qualification. Source bytes/JSON exist only in process RAM."""
from collections import Counter, defaultdict
from decimal import Decimal
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import zlib

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SCOPE = json.loads((OUT / "scope-and-budget.json").read_text())
LIMITS = SCOPE["limits"]
OPTIONS = "-c default_transaction_read_only=on -c default_transaction_isolation=repeatable\\ read -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=15000 -c max_parallel_workers_per_gather=0"
NOW = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
SHA = lambda value: hashlib.sha256(value).hexdigest()
MISSING = object()
ID = re.compile(r"^[mltpsa]_[A-Za-z0-9]{6}$")
SAFE_TEXT_KEYS = {"frame", "coordinate_frame", "unit", "period", "period_code", "format_type", "status", "event_type", "lineup_type", "side", "season", "type"}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def error_text(error):
    text = re.sub(r"postgres(?:ql)?://[^\s'\"]+", "[REDACTED_DSN]", str(error))
    return re.sub(r"(?i)(password\s*=\s*)[^\s]+", r"\1[REDACTED]", text)


def decimal_spelling(value):
    if not value.is_finite():
        raise ValueError("Nonfinite source number")
    sign, digits, exponent = value.as_tuple()
    if not any(digits):
        return "0"
    text = ''.join(map(str, digits))
    if exponent >= 0:
        number = text + '0' * exponent
    else:
        point = len(text) + exponent
        integer, fraction = (text[:point], text[point:]) if point > 0 else ('0', '0' * (-point) + text)
        fraction = fraction.rstrip('0')
        number = integer + ('.' + fraction if fraction else '')
    return ('-' if sign else '') + number


def tagged(value):
    if value is MISSING:
        return ["absent"]
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["boolean", value]
    if isinstance(value, (int, Decimal)):
        return ["number", decimal_spelling(Decimal(value))]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, list):
        return ["array", [tagged(v) for v in value]]
    return ["object", [[k, tagged(v)] for k, v in sorted(value.items())]]


def digest(value):
    return SHA(json.dumps(tagged(value), ensure_ascii=False, separators=(',', ':')).encode())


def state(value):
    if value is MISSING:
        return "absent"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, Decimal)):
        return "number"
    if isinstance(value, str):
        return "empty_string" if value == "" else "string"
    if isinstance(value, list):
        return "empty_list" if not value else "array"
    return "empty_object" if not value else "object"


def value_info(value, key=""):
    result = {"state": state(value), "typedSha256": digest(value)}
    if isinstance(value, (list, dict, str)):
        result["length"] = len(value)
    if value is None or isinstance(value, (int, Decimal, bool)):
        result["value"] = str(value) if isinstance(value, Decimal) else value
    if isinstance(value, str) and (ID.fullmatch(value) or (key in SAFE_TEXT_KEYS and len(value) <= 100) or (re.match(r'^20\d\d-\d\d-\d\d', value) and len(value) <= 80)):
        result["qualifier"] = value
    if isinstance(value, str) and (re.fullmatch(r'[0-9a-f]{64}', value) or (key in {'path','file'} and value.startswith(('computed/', 'raw/')))):
        result['metadataQualifier'] = value
    return result


def shape(value):
    fields = defaultdict(Counter)
    arrays, ids, clocks, enums = {}, defaultdict(set), [], defaultdict(Counter)
    numeric, boolean, numeric_strings = {}, defaultdict(Counter), Counter()

    def visit(node, path="$", key=""):
        fields[path][state(node)] += 1
        if isinstance(node, dict):
            for name, child in node.items():
                visit(child, path + "." + name, name)
        elif isinstance(node, list):
            entry = arrays.setdefault(path, {"collections": 0, "elements": 0, "minimumLength": len(node), "maximumLength": len(node), "duplicateDirectIds": 0})
            entry["collections"] += 1
            entry["elements"] += len(node)
            entry["minimumLength"] = min(entry["minimumLength"], len(node))
            entry["maximumLength"] = max(entry["maximumLength"], len(node))
            direct = [child.get("id") for child in node if isinstance(child, dict) and isinstance(child.get("id"), str)]
            entry["duplicateDirectIds"] += len(direct) - len(set(direct))
            for child in node:
                visit(child, path + "[]", key)
        elif isinstance(node, bool):
            boolean[path][str(node).lower()] += 1
        elif isinstance(node, (int, Decimal)):
            number = Decimal(node)
            sign, digits, exponent = number.as_tuple()
            item = numeric.setdefault(path, {'observations':0,'zero':0,'integerTokens':0,'decimalTokens':0,'maximumFractionalPlaces':0,'maximumIntegerDigits':0})
            item['observations'] += 1
            item['zero'] += number == 0
            item['integerTokens'] += type(node) is int
            item['decimalTokens'] += isinstance(node, Decimal)
            item['maximumFractionalPlaces'] = max(item['maximumFractionalPlaces'], max(0, -exponent))
            item['maximumIntegerDigits'] = max(item['maximumIntegerDigits'], max(1, len(digits) + exponent))
        elif isinstance(node, str):
            if ID.fullmatch(node):
                ids[path].add(node)
            if key in SAFE_TEXT_KEYS and len(node) <= 100:
                enums[path][node] += 1
            if re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', node):
                numeric_strings[path] += 1
            if re.match(r'^20\d\d-\d\d-\d\d', node) and len(node) <= 80:
                lower = key.lower()
                meaning = "business_time_or_unqualified_source_clock"
                if any(part in lower for part in ["retriev", "collect", "fetch", "observed"]):
                    meaning = "observation_clock_not_supplier_revision"
                elif "generat" in lower:
                    meaning = "representation_generation_clock"
                clocks.append({"path": path, "value": node, "meaning": meaning})

    visit(value)
    return {"fieldStates": {p: dict(c) for p, c in sorted(fields.items())}, "arrays": arrays,
        "qualifyingIds": {p: sorted(v) for p, v in sorted(ids.items())},
        "enumValues": {p: dict(c) for p, c in sorted(enums.items())}, "clockCandidates": clocks,
        "numericPrecision": numeric, "booleanValues": {p:dict(c) for p,c in boolean.items()}, "numericStringObservations": dict(numeric_strings),
        "supplierRevisionOrderingProved": False}


def manifest_metadata(value):
    pointers = []
    def visit(node, path='$'):
        if isinstance(node, dict):
            candidate = node.get('leagueId') == 'l_3FJFUl' or node.get('league_id') == 'l_3FJFUl' or node.get('id') == 'l_3FJFUl'
            candidate = candidate or any(isinstance(v,str) and 'l_3FJFUl-' in v and v.startswith('computed/') for v in node.values())
            if candidate:
                allowed = {}
                for k,v in node.items():
                    if isinstance(v,(str,int,Decimal,bool)) and (k in {'leagueId','league_id','id','season','path','file','bytes','sha256','sourceDigest','neonDigest','generation','representationVersion','datasetGeneration','catalogGeneration'}):
                        allowed[k] = str(v) if isinstance(v,Decimal) else v
                if allowed:
                    pointers.append({'jsonPath':path,'metadata':allowed})
            for key, child in node.items():
                visit(child,path+'.'+key)
        elif isinstance(node,list):
            for i,child in enumerate(node):visit(child,path+'['+str(i)+']')
    visit(value)
    return {'qualifiedLeagueMetadata':pointers,'followedPartitionBodies':0,
        'rootMetadata':{k:value[k] for k in ['version','generatedAt','generated_at','generation','representationVersion','datasetGeneration','catalogGeneration','sourceDigest'] if isinstance(value,dict) and k in value and isinstance(value[k],(str,int,bool))}}


def unwrap(node):
    for _ in range(4):
        if not isinstance(node, dict):
            break
        key = next((k for k in ["observation", "response"] if isinstance(node.get(k), dict)), None)
        if key is None:
            break
        node = node[key]
    return node


def qualify(target, parsed):
    if target["kind"] == "manifest":
        return [{"kind": "manifest", "selector": "entire exact object version", "qualified": isinstance(parsed, dict), "responseIds": "not_applicable"}], {"manifest": parsed}
    qualifications, selections = [], {}
    for selector in target["selectors"]:
        endpoint = selector["endpoint"]
        match = re.match(r'^/matches/(m_[A-Za-z0-9]{6})(?:/|$)', endpoint)
        league = re.match(r'^/leagues/(l_[A-Za-z0-9]{6})/matches$', endpoint)
        expected = match.group(1) if match else league.group(1) if league else None
        node = parsed
        choice = {"endpoint": endpoint, "params": selector["params"], "expectedId": expected, "expectedHttpStatus": selector["status"], "refOrdinal": selector["ref_ordinal"]}
        if selector["ref_ordinal"] is not None:
            ordinal = int(selector["ref_ordinal"])
            if not isinstance(node, list) or not 0 <= ordinal < len(node):
                qualifications.append({**choice, "qualified": False, "error": "exact_ordinal_unresolved"})
                continue
            node = node[ordinal]
            choice["selection"] = "exact_recorded_ordinal"
        elif isinstance(node, list):
            candidates = []
            for ordinal, item in enumerate(node):
                response = unwrap(item)
                data = response.get("data") if isinstance(response, dict) else None
                wrapper_id = item.get("matchId") if isinstance(item, dict) else None
                response_id = data.get("match_id") if isinstance(data, dict) else None
                if expected is not None and expected in [wrapper_id, response_id]:
                    candidates.append((ordinal, item))
            choice["candidateMembers"] = len(candidates)
            if len(candidates) != 1:
                qualifications.append({**choice, "qualified": False, "error": "archive_member_not_unique"})
                continue
            choice["selectedOrdinal"], node = candidates[0]
            choice["selection"] = "unique_exact_matchId_member"
        else:
            choice["selection"] = "entire_resource_pointer_value"
        wrapper_id = node.get("matchId") if isinstance(node, dict) else None
        response = unwrap(node)
        data = response.get("data", MISSING) if isinstance(response, dict) else MISSING
        actual_status = response.get("status") if isinstance(response, dict) else None
        response_ids = []
        if isinstance(data, dict):
            if match:
                response_ids = [data[k] for k in ["match_id", "matchId"] if isinstance(data.get(k), str)]
                if endpoint == "/matches/" + expected and isinstance(data.get("id"), str):
                    response_ids.append(data["id"])
            elif league:
                if isinstance(data.get("league"), dict) and isinstance(data["league"].get("id"), str):
                    response_ids.append(data["league"]["id"])
                response_ids += [data[k] for k in ["league_id", "leagueId"] if isinstance(data.get(k), str)]
        observed = list(dict.fromkeys(([wrapper_id] if wrapper_id else []) + response_ids))
        wrong = [identity for identity in observed if identity != expected]
        body_status_ok = actual_status == selector["status"]
        qualified = body_status_ok and bool(observed) and not wrong and data is not MISSING
        choice.update(bodyHttpStatus=actual_status, observedContextIds=observed, contradictoryIds=wrong,
            responseIdState="present" if response_ids else "absent", dataState=state(data),
            qualified=qualified, qualificationLimit=None if qualified else "response_identity_status_or_data_contract_unverified")
        qualifications.append(choice)
        selections[endpoint + " " + selector["params"]] = data
    return qualifications, selections


def duplicate_guard(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key; acceptance blocked")
        result[key] = value
    return result


def decode(raw, budget):
    remaining = LIMITS["decodedBytesMaximum"] - budget["decodedBytes"]
    maximum = min(remaining, LIMITS["decodedObjectBytesMaximum"])
    if maximum <= 0:
        raise ValueError("Global decoded-byte budget exhausted")
    if raw.startswith(b'\x1f\x8b'):
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            body = decoder.decompress(raw, maximum)
        except zlib.error:
            budget["decodedBytes"] += maximum
            raise ValueError("Invalid gzip; conservative decode reserve charged")
        budget["decodedBytes"] += len(body)
        if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
            raise ValueError("Gzip limit, trailing data or concatenated member blocks acceptance")
    else:
        if len(raw) > maximum:
            raise ValueError("Plain JSON exceeds remaining decoded budget")
        body = raw
        budget["decodedBytes"] += len(body)
    return json.loads(body.decode('utf-8'), parse_float=Decimal, parse_int=int, object_pairs_hook=duplicate_guard,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON number"))), len(body)


PREFLIGHT_SQL = """WITH wanted AS (SELECT * FROM jsonb_to_recordset(%s::jsonb) AS w(path text)),
 wanted_selectors AS (SELECT * FROM jsonb_to_recordset(%s::jsonb) AS s(endpoint text,params text)),
 rows AS (SELECT w.path,o.size,encode(o.sha256,'hex') AS stored_sha256,octet_length(o.body) AS physical_bytes,o.updated_at,
 CASE WHEN octet_length(o.body)>=18 AND get_byte(o.body,0)=31 AND get_byte(o.body,1)=139 THEN
 get_byte(o.body,octet_length(o.body)-4)::bigint+256::bigint*get_byte(o.body,octet_length(o.body)-3)
 +65536::bigint*get_byte(o.body,octet_length(o.body)-2)+16777216::bigint*get_byte(o.body,octet_length(o.body)-1)
 ELSE octet_length(o.body)::bigint END AS announced_decoded_bytes
 FROM wanted w LEFT JOIN statarena.objects o ON o.path=w.path)
 SELECT jsonb_build_object('identity',jsonb_build_object('database',current_database(),'role',current_user,
 'snapshot',pg_current_snapshot()::text,'read_only',current_setting('transaction_read_only'),
 'isolation',current_setting('transaction_isolation'),'statement_timeout',current_setting('statement_timeout'),
 'lock_timeout',current_setting('lock_timeout'),'observed_at',clock_timestamp()),
 'objects',(SELECT jsonb_agg(to_jsonb(r) ORDER BY path) FROM rows r),
 'selectors',(SELECT jsonb_agg(jsonb_build_object('endpoint',s.endpoint,'params',s.params,'status',r.status,
 'ref_path',coalesce(r.ref->>'path',r.ref->>'shard'),'ref_ordinal',r.ref->>'ordinal','updated_at',r.updated_at))
 FROM wanted_selectors s LEFT JOIN statarena.resources r ON r.endpoint=s.endpoint AND r.params=s.params)) AS preflight"""
BODY_SQL = """WITH wanted AS (SELECT * FROM jsonb_to_recordset(%s::jsonb) AS w(path text,expected_sha text,expected_size bigint))
 SELECT o.path,o.body FROM wanted w JOIN statarena.objects o ON o.path=w.path
 WHERE encode(o.sha256,'hex')=w.expected_sha AND o.size=w.expected_size
 AND octet_length(o.body)=w.expected_size AND octet_length(o.body)<=2097152 ORDER BY o.path"""


def connect(source):
    import psycopg
    from psycopg.rows import dict_row
    settings = dict(options=OPTIONS, connect_timeout=7, autocommit=False, row_factory=dict_row, sslmode="verify-full", application_name="statarena-content-qualification-ro")
    if source == "neon":
        line = next(line for line in (ROOT / "dashboard/.env").read_text().splitlines() if line.strip().startswith("NEON_DATABASE_URL="))
        dsn = line.split('=', 1)[1].strip().strip('"').strip("'")
        dsn = dsn.replace("ep-steep-boat-bekuqo4w-pooler.", "ep-steep-boat-bekuqo4w.")
        return psycopg.connect(dsn, sslrootcert="/etc/ssl/cert.pem", **settings)
    return psycopg.connect(host="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com", dbname="statarena_prod", user="statarena_ingest",
        sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"), **settings)


def read_source(source, budget, ram):
    targets = [t for t in SCOPE["targets"] if t["source"] == source]
    selectors = {(s["endpoint"], s["params"]): s for t in targets for s in t["selectors"]}
    record = {"source": source, "startedAt": NOW(), "remoteWrites": [], "bodyPersistence": False, "objects": []}
    connection = None
    try:
        connection = connect(source)
        params = connection.info.get_parameters()
        record["clientTls"] = {"sslInUse": connection.pgconn.ssl_in_use, **{k: params.get(k) for k in ["host", "dbname", "sslmode", "sslrootcert"]}}
        if not record["clientTls"]["sslInUse"] or params.get('sslmode') != 'verify-full':
            raise ValueError("TLS client verify-full precondition failed")
        budget["sqlInstructions"] += 2  # implicit BEGIN + preflight SELECT
        preflight = connection.execute(PREFLIGHT_SQL, (json.dumps([{"path": t["path"]} for t in targets]), json.dumps([{"endpoint": k[0], "params": k[1]} for k in selectors]))).fetchone()["preflight"]
        record["preflight"] = preflight
        identity = preflight["identity"]
        if not (identity['read_only'] == 'on' and identity['isolation'] == 'repeatable read' and identity['statement_timeout'] == '8s'):
            raise ValueError("Snapshot RO/RR/deadline precondition failed")
        current = {x["path"]: x for x in preflight["objects"]}
        actual_selectors = {(x["endpoint"], x["params"]): x for x in preflight["selectors"] or []}
        admitted = []
        reserve = 0
        for target in targets:
            metadata = current[target["path"]]
            failures = []
            if metadata.get('stored_sha256') != target['expectedPhysicalSha256'] or metadata.get('size') != target['expectedPhysicalBytes'] or metadata.get('physical_bytes') != target['expectedPhysicalBytes']:
                failures.append('frozen_physical_metadata_changed_or_missing')
            if (metadata.get('physical_bytes') or 0) > LIMITS['physicalObjectBytesMaximum']:
                failures.append('physical_size_preflight_limit')
            declared = metadata.get('announced_decoded_bytes')
            if declared is None or declared > LIMITS['decodedObjectBytesMaximum'] or declared + reserve + budget['decodedBytes'] > LIMITS['decodedBytesMaximum']:
                failures.append('announced_decoded_size_preflight_limit')
            for selector in target['selectors']:
                now = actual_selectors.get((selector['endpoint'], selector['params']))
                if now is None or any(now.get(k) != selector.get(k) for k in ['status', 'ref_path', 'ref_ordinal']):
                    failures.append('frozen_resource_selector_changed')
            if failures:
                record['objects'].append({'path': target['path'], 'status': 'blocked_before_fetch', 'failures': failures})
            else:
                reserve += declared
                admitted.append(target)
        if admitted:
            budget['sqlInstructions'] += 1
            payloads = connection.execute(BODY_SQL, (json.dumps([{'path': t['path'], 'expected_sha': t['expectedPhysicalSha256'], 'expected_size': t['expectedPhysicalBytes']} for t in admitted]),)).fetchall()
            by_path = {t['path']: t for t in admitted}
            for row in payloads:
                target = by_path[row['path']]
                raw = bytes(row['body'])
                result = {'path': target['path'], 'physicalBytes': len(raw), 'expectedPhysicalSha256': target['expectedPhysicalSha256'], 'actualPhysicalSha256': SHA(raw)}
                try:
                    if SHA(raw) != target['expectedPhysicalSha256']:
                        raise ValueError('Physical SHA does not match frozen expected version')
                    parsed, decoded_bytes = decode(raw, budget)
                    if decoded_bytes != current[target['path']]['announced_decoded_bytes']:
                        raise ValueError('Gzip/plain decoded size disagrees with announced size')
                    qualifications, selections = qualify(target, parsed)
                    result.update(status='decoded', decodedBytes=decoded_bytes, decodedTypedSha256=digest(parsed), rootState=state(parsed),
                        qualifications=qualifications, shape=shape(parsed), selectionSummaries={k: {'state': state(v), 'typedSha256': digest(v), 'shape': shape(v)} for k, v in selections.items()})
                    if target['kind']=='manifest':
                        result['manifestMetadata'] = manifest_metadata(parsed)
                    ram[(source, target['path'])] = {'parsed': parsed, 'selections': selections}
                except Exception as error:
                    result.update(status='blocked_after_fetch', errorType=type(error).__name__, error=error_text(error))
                record['objects'].append(result)
            missing = set(by_path) - {row['path'] for row in payloads}
            for path in sorted(missing):
                record['objects'].append({'path': path, 'status': 'blocked_before_fetch', 'failures': ['admitted_payload_not_returned']})
            del payloads
        record['status'] = 'read_completed'
    except Exception as error:
        record.update(status='blocked', errorType=type(error).__name__, error=error_text(error))
    finally:
        if connection is not None:
            budget['sqlInstructions'] += 1
            try:
                connection.rollback()
            except Exception as error:
                record['rollbackError'] = error_text(error)
            finally:
                connection.close()
        record['finishedAt'] = NOW()
        save(source + '-content.json', record)
        print(json.dumps({'source': source, 'status': record['status'], 'decodedObjects': sum(r['status']=='decoded' for r in record['objects']), 'blockedObjects': sum(r['status']!='decoded' for r in record['objects']), 'error': record.get('error'), 'sqlInstructionsCumulative': budget['sqlInstructions'], 'decodedBytesCumulative': budget['decodedBytes']}), flush=True)


def differences(left, right, path='$', output=None):
    output = output if output is not None else []
    if digest(left) == digest(right):
        return output
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            differences(left.get(key, MISSING), right.get(key, MISSING), path + '.' + key, output)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            output.append({'path': path, 'kind': 'collection_length', 'neonLength': len(left), 'awsLength': len(right)})
        for i in range(max(len(left), len(right))):
            differences(left[i] if i < len(left) else MISSING, right[i] if i < len(right) else MISSING, path + '[' + str(i) + ']', output)
    else:
        output.append({'path': path, 'neon': value_info(left, path.rsplit('.',1)[-1]), 'aws': value_info(right, path.rsplit('.',1)[-1])})
    return output


def pair_results(ram):
    result = []
    for pair in SCOPE['pairs']:
        n = ram.get(('neon', pair['neonPath']))
        a = ram.get(('aws', pair['awsPath']))
        if not n or not a:
            result.append({**pair, 'status': 'unverified_missing_qualified_decode'})
            continue
        key = 'manifest' if pair['kind']=='manifest' else pair['key']['endpoint'] + ' ' + pair['key']['params']
        left, right = n['selections'].get(key, MISSING), a['selections'].get(key, MISSING)
        changes = differences(left, right)
        result.append({**pair, 'status': 'compared_selected_content', 'neonTypedSha256': digest(left), 'awsTypedSha256': digest(right),
            'equalSelectedTypedContent': digest(left)==digest(right), 'differenceCount': len(changes), 'differenceLimit': 1000,
            'differences': changes[:1000], 'differencesTruncated': len(changes)>1000,
            'arrayAlignmentPolicy': 'Exact source order retained; differing array positions do not establish entity-level updates without a separately accepted unique key',
            'supplierFreshnessOrdering': 'unverified'})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hold', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if (OUT / 'execution.json').exists() or (OUT / 'neon-content.json').exists():
        raise SystemExit('Existing live receipts prevent implicit replay or budget reset')
    plan = {'preparedAt': NOW(), 'preflightSql': PREFLIGHT_SQL, 'bodySql': BODY_SQL, 'bodyParameters': 'Only admitted exact scope paths/expected hashes/sizes; no body in recorded parameters',
        'perSourceParameters': {source: {'objects': [{'path': t['path']} for t in SCOPE['targets'] if t['source']==source],
            'selectors': list({(s['endpoint'],s['params']): {'endpoint': s['endpoint'], 'params': s['params']} for t in SCOPE['targets'] if t['source']==source for s in t['selectors']}.values())} for source in ['neon','aws']},
        'startupOptions': OPTIONS, 'sqlMaximum': 18, 'nominalIncludingControls': 8}
    if not (OUT/'query-plan.json').exists():
        save('query-plan.json', plan)
    if args.prepare_only:
        print(json.dumps({'prepared':True,'nominalInstructions':8,'maximumInstructions':18,'queryPlanSha256':SHA((OUT/'query-plan.json').read_bytes())}))
        return
    budget = {'sqlInstructions': 0, 'decodedBytes': 0, 'limits': LIMITS}
    ram = {}
    started = NOW()
    for source in ['neon','aws']:
        if budget['sqlInstructions'] + 4 > LIMITS['sqlInstructionsMaximum']:
            raise SystemExit('SQL budget prevents next source')
        read_source(source, budget, ram)
    save('content-comparison.json', pair_results(ram))
    execution = {'startedAt': started, 'finishedAt': NOW(), 'budget': budget, 'decodedVersions': len(ram), 'expectedVersions': 14,
        'remoteWrites': [], 'bodyPersistence': False, 'providerRequests': 0, 'fullAcceptance': False,
        'sourceCodeSha256': SHA(Path(__file__).read_bytes()), 'scopeSha256': SHA((OUT/'scope-and-budget.json').read_bytes()),
        'limitsRespected': budget['sqlInstructions'] <= 18 and budget['decodedBytes'] <= 33554432}
    save('execution.json', execution)
    print(json.dumps({'ready': True, 'decodedVersions': len(ram), 'budget': budget}), flush=True)
    if args.hold:
        print('RAM_READY: commands summary / pairs / stop; no command reconnects or prints source bodies', flush=True)
        while True:
            try:
                command = input().strip()
            except EOFError:
                break
            if command == 'stop':
                break
            if command == 'pairs':
                save('content-comparison.json', pair_results(ram))
                print(json.dumps({'pairs': [{'key': r['key'], 'equal': r.get('equalSelectedTypedContent'), 'differences': r.get('differenceCount')} for r in pair_results(ram)]}), flush=True)
            elif command == 'summary':
                print(json.dumps({'decodedVersions': len(ram), 'budget': budget}), flush=True)
            else:
                print('Unknown safe command; bodies are never exposed', flush=True)
    ram.clear()
    save('ram-cleanup.json', {'atUtc': NOW(), 'state': 'parsed content references released; reader exiting', 'remoteWrites': [], 'bodyFilesWritten': []})


if __name__ == '__main__':
    main()
