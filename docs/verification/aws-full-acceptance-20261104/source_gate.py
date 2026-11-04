"""Audit source metadata against committed relational receipts. Never dispatch a worker."""
import argparse
import collections
import datetime
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import psycopg

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
sys.path.insert(0, str(ROOT / "dashboard/scripts"))
from relational_materialize import CATALOG_PATHS, PROFILE, INDEX, FAMILIES, compact
from relational_match import _resource_address, canonical
from relational_materialize import MESSI, overlay_rounds
from relational_catalog_keys import records as catalog_records
from relational_catalog import model_version
from relational_support import _MODEL_VERSION, _canonical

MD5 = lambda value: hashlib.md5(value.encode()).hexdigest()


def connection():
    secret = json.loads(subprocess.check_output([
        "aws", "--profile", "statarena", "--region", "us-east-2", "ssm", "get-parameter",
        "--name", "/statarena/app/rds-runtime", "--with-decryption", "--query", "Parameter.Value", "--output", "text",
    ]))
    assert secret["host"] == "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com" and secret["database"] == "statarena_prod"
    return psycopg.connect(host=secret["host"], dbname=secret["database"], user=secret["username"],
        password=secret["password"], sslmode="verify-full", sslrootcert=str(ROOT/"dashboard/backend/certs/rds-us-east-2.pem"),
        connect_timeout=7, application_name="statarena-final-source-audit",
        options="-c default_transaction_read_only=on -c statement_timeout=20000 -c lock_timeout=1000 -c max_parallel_workers_per_gather=0")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", help="allow the full structural comparison after completion")
    parser.add_argument("--out", required=True, type=Path, help="new evidence directory")
    opts = parser.parse_args()
    opts.out.mkdir(parents=True, exist_ok=False)
    report = {"status": "unverified", "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "command": sys.argv, "revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "counts": {}, "exceptions": {}, "failedChecks": {}}
    counts = collections.Counter()
    named = (opts.out/"exceptions.jsonl").open("w")
    def issue(kind, key, expected=None, actual=None, failure=True):
        section = "failedChecks" if failure else "exceptions"
        report[section][kind] = 1 + report[section].get(kind, 0)
        named.write(json.dumps(dict(kind=kind, key=key, expected=expected, actual=actual, failure=failure), default=str, ensure_ascii=False)+"\n")

    def run(db):
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        def rows(sql, args=()):
            return db.execute(sql, args).fetchall()
        def one(sql, args=()):
            return db.execute(sql, args).fetchone()
        identity = one("SELECT current_database(),current_setting('transaction_read_only'),current_setting('TimeZone'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())")
        assert identity[0:2] == ("statarena_prod", "on") and identity[3]
        report["identity"] = identity
        state = one("SELECT status,remaining,completed_at FROM statarena_app.workflow_state WHERE workflow='relational-materialize'")
        guard = one("SELECT generation,(SELECT count(*) FROM statarena_app.publication_jobs),(SELECT count(*) FROM statarena.dirty_partitions) FROM statarena_app.publications WHERE singleton")
        report["generation"], report["queuedScopes"], report["dirtyScopes"] = guard
        report["workerState"] = state
        if not state or state[0] != "complete" or state[1] or state[2] is None or any(guard[1:]):
            report["status"] = "waiting"
            return
        if not opts.audit:
            report["status"] = "ready_for_source_audit"
            return
        installed = dict(rows("SELECT version,digest FROM statarena_app.worker_schema"))
        for p in sorted((ROOT/"dashboard/backend/migrations").glob("0[0-9][0-9]_*.sql")):
            if int(p.name[:3]) >= 3 and hashlib.sha256(p.read_bytes()).hexdigest() != installed.get(p.name):
                issue("schema-pin", p.name, hashlib.sha256(p.read_bytes()).hexdigest(), installed.get(p.name))
        expected = {}
        def expect(kind, key, digest):
            expected[kind,key] = digest
            counts["expected:"+kind] += 1
        stored = {(kind,key):h for kind,key,h in rows("SELECT kind,key,digest FROM statarena_app.worker_inputs")}
        scopes = set(rows("SELECT season,league_id FROM statarena_app.partitions"))
        manifest = one("SELECT d.document,encode(o.sha256,'hex') FROM statarena.current_file_documents d JOIN statarena.objects o ON o.path=d.source_path WHERE d.source_path=%s AND d.document_path=d.source_path", (INDEX,))
        if not manifest:
            raise ValueError("Missing current staging manifest")
        report["manifestSha256"] = manifest[1]
        chunks = {(s["id"],c["leagueId"]):c for s in manifest[0]["seasons"] for c in s["chunks"]}
        counts["manifestScopes"] = len(chunks)
        physical = dict(rows("SELECT path,encode(sha256,'hex') FROM statarena.objects WHERE path=ANY(%s)", ([c["path"] for c in chunks.values()],)))
        for sel,c in chunks.items():
            if sel not in scopes:
                issue("unpublished-manifest-partition", sel)
            if c["path"] not in physical or (c.get("sha256") and c["sha256"] != physical[c["path"]]):
                issue("manifest-chunk-pin", sel, c.get("sha256"), physical.get(c["path"]))
        # The worker deliberately publishes additional fixture scopes and orphan detail buckets.
        # Return just per-resource fingerprints and statuses; source payloads never cross the connection.
        samples = {}
        statuses = collections.Counter()
        source_missing = collections.Counter()
        saved = collections.defaultdict(list)
        typed = {(m,f,s,p):status for m,f,s,p,status in rows("SELECT match_id,family,subject_id,params,status FROM statarena_app.match_families")}
        def check_ref(key,path,claimed,actual):
            if path and (not actual or (claimed and claimed != actual and not (
                    re.fullmatch(r"[0-9a-f]{64}",claimed) and path == f"raw/pitchapi-world/blobs/{claimed}.json.gz"))):
                issue("unresolved-source-reference", key, [path,claimed], actual)
        # One statement uses the source table primary-key ordering. The driver streams in batches.
        with db.cursor(name="accept_saved") as cur:
            cur.itersize=2048
            cur.execute("""SELECT r.endpoint,r.params,r.status,r.ref->>'path',r.ref->>'sha256',encode(o.sha256,'hex'),
                md5(r.endpoint||r.params||r.xmin::text||r.status::text||r.updated_at::text||coalesce(r.ref::text,'')||
                    coalesce(r.error::text,'')||coalesce(encode(o.sha256,'hex'),'')) FROM statarena.resources r
                LEFT JOIN statarena.objects o ON o.path=r.ref->>'path' WHERE starts_with(r.endpoint,'/matches/') ORDER BY r.endpoint,r.params""")
            for ep,p,status,path,claimed,actual,h in cur:
                mid=ep.split("/")[2]
                saved[mid].append(h)
                check_ref([ep,p],path,claimed,actual)
                addr=_resource_address(ep)
                if not addr:
                    issue("unmapped-saved-match", [ep,p])
                    continue
                m,f,sub=addr
                selector=(m,f,sub,canonical(json.loads(p)))
                statuses[f,status]+=1
                try:
                    params=json.loads(p)
                    exposed=not params or (f=="heatmaps" and params in ({"frame":"acting_ltr"},{"frame":"home_ltr"}))
                except (TypeError,ValueError):
                    exposed=False
                if exposed: samples.setdefault(("match",f,status,canonical(params)),dict(endpoint=ep,params=p,status=status,family=f,scope="match"))
                else: issue("stored-selector-outside-public-parameter-contract",[ep,p],status,typed.get(selector),False)
                if typed.get(selector) != status:
                    issue("saved-match-status-or-missing", [ep,p], status, typed.get(selector))
                elif status != 200:
                    source_missing[f,status]+=1
                    issue("saved-unavailable-match", [ep,p],status,status,False)
        saved = {m:MD5("".join(h)) for m,h in saved.items()}
        report["savedMatchSourceStatusCounts"] = {str(k):v for k,v in sorted(statuses.items())}
        report["savedUnavailableWithTypedStatus"] = {str(k):v for k,v in sorted(source_missing.items())}
        shard = dict(rows("""SELECT s.id,md5(s.ref::text||coalesce(string_agg(path||coalesce(encode(o.sha256,'hex'),''),'|' ORDER BY path),''))
          FROM statarena.shards s LEFT JOIN LATERAL (SELECT s.ref#>>'{document,path}' path UNION ALL SELECT value->>'path' FROM jsonb_each(s.ref->'tables')) refs ON true
          LEFT JOIN statarena.objects o USING(path) GROUP BY s.id,s.ref"""))
        obs = {i:(s,n) for i,s,n in rows("SELECT id,shard,ordinal FROM statarena.observations")}
        groups = {}
        for m,l,y,prefix in rows("""SELECT id,league_id,season,xmin::text||updated_at::text FROM statarena.fixtures WHERE season ~ '^[0-9]{4}(/[0-9]{4})?$'"""):
            if (y,l) not in chunks and len(y)==4:
                y=y+"/"+str(int(y)+1)
            sid,n=obs.get(m,(None,None))
            if sid and sid not in shard:
                issue("observation-shard-missing",m,sid)
            groups[m]=(y,l,MD5(prefix+(sid or "")+(str(n) if n is not None else "")+shard.get(sid,"")+saved.get(m,"")))
        orphan=lambda m:("@details","@details-"+MD5(m)[:2])
        for m,h in saved.items():
            if re.fullmatch(r"m_[A-Za-z0-9]{6}",m) and m not in groups:
                groups[m]=(*orphan(m),h)
        for m,(sid,n) in obs.items():
            if sid not in shard:
                issue("missing-shard",m,sid)
                continue
            if m in groups and groups[m][0]!="@details":
                continue
            h=MD5(sid+str(n)+shard[sid])
            groups[m]=(*orphan(m),MD5(groups[m][2]+h) if m in groups else h)
        # Obtain PostgreSQL's ordering for string_agg, including collation and wrapped seasons.
        ordered=rows("SELECT m FROM unnest(%s::text[]) t(m) ORDER BY m",(list(groups),))
        assembled=collections.defaultdict(list)
        for (m,) in ordered:
            y,l,h=groups[m];assembled[y,l].append(m+h)
        profiles = {(ep,p):(h,status,path,claimed,obj) for ep,p,h,status,path,claimed,obj in rows("""SELECT r.endpoint,r.params,
          md5(r.xmin::text||r.updated_at::text||r.status::text||coalesce(r.ref::text,'')||coalesce(r.error::text,'')||coalesce(encode(o.sha256,'hex'),'')),
          r.status,r.ref->>'path',r.ref->>'sha256',encode(o.sha256,'hex') FROM statarena.resources r
          LEFT JOIN statarena.objects o ON o.path=r.ref->>'path' WHERE r.params='{}' AND r.endpoint ~ %s""",(PROFILE,))}
        league_revs=dict(rows("""SELECT r.endpoint,r.xmin::text||coalesce(encode(o.sha256,'hex'),'') FROM statarena.resources r
          LEFT JOIN statarena.objects o ON o.path=r.ref->>'path' WHERE r.params='{}' AND starts_with(r.endpoint,'/leagues/')"""))
        for (y,l),pieces in assembled.items():
            if y!="@details" and (y,l) not in scopes: issue("unpublished-fixture-partition",[y,l])
            expect("partition",y+":"+l,MD5("".join(pieces)+league_revs.get("/leagues/"+l,"")))
        catalog=dict(((s,e),n) for s,e,n in rows("SELECT scope,edition,response_status FROM statarena_app.catalog_editions WHERE catalog='profile'"))
        for (ep,p),(h,status,path,claimed,obj) in profiles.items():
            expect("profile",ep,h)
            check_ref(ep,path,claimed,obj)
            parts=ep.strip("/").split("/")
            actual=catalog.get((parts[0],parts[1] if len(parts)>1 else ""))
            if len(parts)>1 or ep=="/leagues":
                variant=parts[0] if len(parts)>1 else ep+"-list"
                samples.setdefault(("profile",variant,status,p),dict(endpoint=ep,params=p,status=status,family=variant,scope="profile"))
            if actual!=status:issue("unpublished-or-wrong-profile-status",ep,status,actual)
            elif status!=200:issue("saved-unavailable-profile",ep,status,actual,False)
        # Retained physical copies are only used if they match the current RDS SHA.
        # Changed catalog inputs use their exact indexed source. Matchday calendars include later detail overlays.
        inventory=json.loads((FOLDER.parent/"aws-catalog-20261104/source-inventory.json").read_text())
        cached={r["path"]:Path("/tmp/statarena-catalog-source-audit-20261104")/r["etag"] for r in inventory}
        deliveries={(k,s,e):h for k,s,e,h in rows("SELECT catalog,scope,edition,source_digest FROM statarena_app.catalog_editions WHERE catalog<>'profile'")}
        for path,h in rows("SELECT path,encode(sha256,'hex') FROM statarena.objects WHERE path~%s OR path='raw/supplemental-index.json'",(CATALOG_PATHS,)):
            expect("object",path,h)
            local=cached.get(path)
            raw=local.read_bytes() if local and local.is_file() else None
            if raw is not None and hashlib.sha256(raw).hexdigest()==h:
                body=json.loads(gzip.decompress(raw) if path.endswith(".gz") else raw)
                counts["pinnedLocalCatalogs"]+=1
            else:
                match=one("SELECT d.document FROM statarena.current_file_documents d JOIN statarena.objects o ON o.path=d.source_path WHERE d.source_path=%s AND d.document_path=d.source_path AND o.sha256=decode(%s,'hex')",(path,h))
                if not match:
                    issue("no-verified-catalog-body",path,h);continue
                body=match[0];counts["pinnedIndexedCatalogs"]+=1
            if path.startswith("computed/matchdays/"):
                label=path.rsplit("/",1)[1].removesuffix(".json.gz").replace("-","/")
                body=overlay_rounds(db,label,body)
            for _,kind,scope,edition,value in catalog_records(path,body):
                selector=kind,scope,edition
                digest=hashlib.sha256((model_version+canonical(value)).encode()).hexdigest()
                if deliveries.get(selector)!=digest:issue("typed-catalog-edition-pin",selector,digest,deliveries.get(selector))
                counts["checkedEditionPins"]+=1
        ph=one("SELECT md5(coalesce(string_agg(name||params||xmin::text||updated_at::text,'' ORDER BY name,params),'')) FROM statarena.projections WHERE name=ANY(%s)",(list(FAMILIES),))[0]
        curated=hashlib.sha256((ROOT/"dashboard/scripts/materialize_curated.mjs").read_bytes()+(ROOT/"dashboard/shared/honour-display.js").read_bytes()).hexdigest()
        expect("global","support",ph+curated)
        support={(name,compact(json.loads(p))):body for name,p,body in rows("SELECT name,params,body FROM statarena.projections WHERE name=ANY(%s)",(list(FAMILIES),))}
        curated_rows=json.loads(subprocess.run(["node",str(ROOT/"dashboard/scripts/materialize_curated.mjs")],input=compact(support.get(MESSI)),text=True,capture_output=True,check=True,timeout=90).stdout)
        for r in curated_rows:support[(r["name"],compact(r["params"]))]=r["body"]
        support_actual={(name,p):h for name,p,h in rows("SELECT name,params,digest FROM statarena_app.support_projection")}
        for k,v in support.items():
            h=hashlib.sha256(_MODEL_VERSION+_canonical(v).encode()).hexdigest()
            if support_actual.get(k)!=h:issue("typed-support-pin",k,h,support_actual.get(k))
        counts["effectiveSupportKeys"]=len(support)
        for k,h in expected.items():
            if stored.get(k)!=h:issue("worker-input-missing-or-changed",k,h,stored.get(k))
        for k in stored.keys()-expected.keys():
            issue("no-current-source-for-receipt",k,stored[k],None)
        for url,path in rows("""SELECT a.url,a.path FROM statarena.assets a LEFT JOIN statarena.objects o ON o.path=a.path
           LEFT JOIN statarena_app.assets b ON b.url=a.url WHERE o.path IS NULL OR b.url IS NULL OR
           (b.path,b.content_type,b.size,b.sha256,b.etag) IS DISTINCT FROM (a.path,a.content_type,o.size,encode(o.sha256,'hex'),o.etag)"""):
            issue("asset-unresolved-or-stale",url,path)
        counts.update({"sourceMatchScopes":len(assembled),"publishedPartitions":len(scopes),"typedMatchSelectors":len(typed),"sourceMatchIDs":len(groups),"sourceObservations":len(obs),"orphanScopes":sum(1 for y,l in assembled if y=="@details")})
        report["samples"]=list(samples.values())
        report["receiptUniverseSha256"]=hashlib.sha256(canonical(sorted([k,z,h] for (k,z),h in expected.items())).encode()).hexdigest()
        report["currentManifestChunkPinsSha256"]=hashlib.sha256(canonical(sorted(physical.items())).encode()).hexdigest()
        report["status"]="failed" if report["failedChecks"] else "source_metadata_passed"

    try:
        with connection() as db:
            run(db)
            generation=report.get("generation")
            db.commit()
            now=db.execute("SELECT generation FROM statarena_app.publications WHERE singleton").fetchone()[0]
            if generation is not None and now!=generation:
                issue("generation-moved", "publication", generation, now)
                report["status"]="inconclusive"
    except Exception as e:
        report["status"]="inconclusive"
        report["error"]={"type":type(e).__name__,"sqlstate":getattr(e,"sqlstate",None),
                         "location":getattr(e.__traceback__,"tb_lineno",None)}
    finally:
        named.close()
        report["counts"]=dict(counts)
        (opts.out/"source.json").write_text(json.dumps(report,default=str,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","counts","failedChecks","exceptions")}))
    return 0 if report["status"] in ("source_metadata_passed","ready_for_source_audit") else 1

if __name__=="__main__":
    raise SystemExit(main())
