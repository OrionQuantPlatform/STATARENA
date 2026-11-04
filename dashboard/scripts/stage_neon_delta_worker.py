"""Read a Neon source snapshot directly into a PostgreSQL JSON staging table."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import threading
import time
import urllib.request

import boto3
import psycopg
from botocore.config import Config

from sql_document_parser import iter_documents

parser = argparse.ArgumentParser()
parser.add_argument("--workers", type=int, default=4)
args = parser.parse_args()
if not 1 <= args.workers <= 8:
    raise ValueError("Invalid worker count")
credentials = json.loads(os.environ["STATARENA_PAYLOAD_DB_CREDENTIALS"])
config = {"host": os.environ["STATARENA_PAYLOAD_DB_HOST"], "port": 5432, "dbname": os.environ["STATARENA_PAYLOAD_DB_NAME"],
          "user": "statarena_ingest", "password": credentials["statarena_ingest"], "sslmode": "verify-full",
          "sslrootcert": os.environ["STATARENA_PAYLOAD_DB_CA"], "connect_timeout": 10, "autocommit": True}
ip = urllib.request.urlopen("https://checkip.amazonaws.com", timeout=15).read().decode().strip()
print(json.dumps({"event": "network", "public_ip": ip}), flush=True)
for attempt in range(36):
    try:
        control = psycopg.connect(**config)
        break
    except psycopg.OperationalError:
        if attempt == 35:
            raise
        time.sleep(10)
rows = control.execute("""select q.path,q.size,q.source_sha256,q.content_type,q.target_sha256_at_capture
    from statarena.neon_delta_queue q left join statarena.neon_delta_documents d on d.path=q.path
    where d.path is null or d.source_sha256<>q.source_sha256 order by q.path""").fetchall()
total = control.execute("select count(*) from statarena.neon_delta_queue").fetchone()[0]
print(json.dumps({"event": "inventory", "total": total, "already_staged": total-len(rows), "remaining": len(rows)}), flush=True)
s3 = boto3.client("s3", endpoint_url=os.environ["SOURCE_STORAGE_ENDPOINT"], region_name="us-east-2",
                  aws_access_key_id=os.environ["SOURCE_STORAGE_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["SOURCE_STORAGE_SECRET_ACCESS_KEY"],
                  config=Config(s3={"addressing_style": "path"}, max_pool_connections=args.workers, retries={"max_attempts": 4}))
local = threading.local()
connections = []
lock = threading.Lock()


def stage(row):
    path, size, expected, content_type, target_sha = row
    expected = bytes(expected)
    if not getattr(local, "db", None):
        local.db = psycopg.connect(**config)
        with lock:
            connections.append(local.db)
    prior = local.db.execute("select size,source_sha256 from statarena.neon_delta_documents where path=%s", (path,)).fetchone()
    if prior:
        if prior[0] == size and bytes(prior[1]) == expected:
            return "already_present"
        raise ValueError("A different source version is already staged")
    obj = s3.get_object(Bucket=os.environ["SOURCE_STORAGE_BUCKET"], Key="data/" + path)
    try:
        body = obj["Body"].read()
    finally:
        obj["Body"].close()
    if len(body) != size or hashlib.sha256(body).digest() != expected:
        raise ValueError("Neon source does not match its captured checksum")
    documents = list(iter_documents(path, body))
    if len(documents) != 1 or documents[0][0] != path or documents[0][3] is not None:
        raise ValueError("Source is not a single valid JSON document")
    text = documents[0][2]
    result = local.db.execute("""insert into statarena.neon_delta_documents
        (path,size,source_sha256,content_type,etag,document,target_sha256_at_capture)
        values(%s,%s,%s,%s,%s,%s::jsonb,%s) on conflict(path) do nothing
        returning source_sha256,document=%s::jsonb""",
        (path, size, expected, content_type, obj["ETag"].strip('"'), text, target_sha, text)).fetchone()
    if not result or bytes(result[0]) != expected or not result[1]:
        raise ValueError("SQL verification failed or another version was staged")
    return "copied"


def retry(row):
    for attempt in range(3):
        try:
            return stage(row)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


report = {"total": total, "already_staged": total-len(rows), "copied": 0, "already_present": 0, "failed": 0, "failures": []}
iterator = iter(rows)
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        active = {}
        next_progress = 200
        while True:
            while len(active) < args.workers * 2:
                try:
                    row = next(iterator)
                except StopIteration:
                    break
                active[pool.submit(retry, row)] = row[0]
            if not active:
                break
            done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                path = active.pop(future)
                try:
                    report[future.result()] += 1
                except Exception as error:
                    report["failed"] += 1
                    if len(report["failures"]) < 30:
                        report["failures"].append({"path": path, "error": type(error).__name__})
            completed = report["copied"] + report["already_present"] + report["failed"]
            if completed >= next_progress:
                print(json.dumps({k: v for k, v in report.items() if k != "failures"}), flush=True)
                next_progress = completed + 200
finally:
    control.close()
    for connection in connections:
        connection.close()
print(json.dumps(report), flush=True)
if report["failed"]:
    raise SystemExit("Some Neon JSON documents need another verified pass")
