"""Copy S3 originals into PostgreSQL, verify bytes, and leave S3 unchanged."""
import argparse
import concurrent.futures
import json
import os
import threading
import time
import urllib.request

import boto3
import psycopg
from botocore.config import Config

from sql_payload_store import lock_payload, write_payload

parser = argparse.ArgumentParser()
parser.add_argument("--workers", type=int, default=4)
parser.add_argument("--limit", type=int)
parser.add_argument("--data-prefix")
parser.add_argument("--include-all", action="store_true")
args = parser.parse_args()
if not 1 <= args.workers <= 12 or (args.limit is not None and args.limit < 1):
    raise ValueError("Invalid worker count or limit")
if not args.data_prefix and not args.include_all:
    raise ValueError("Choose a data prefix or explicitly request the complete inventory")

credentials = json.loads(os.environ["STATARENA_PAYLOAD_DB_CREDENTIALS"])
db_config = {"host": os.environ["STATARENA_PAYLOAD_DB_HOST"], "port": 5432, "dbname": os.environ["STATARENA_PAYLOAD_DB_NAME"],
             "user": "statarena_ingest", "password": credentials["statarena_ingest"], "sslmode": "verify-full",
             "sslrootcert": os.environ["STATARENA_PAYLOAD_DB_CA"], "connect_timeout": 10, "autocommit": True}
data_bucket = os.environ["STATARENA_PAYLOAD_DATA_BUCKET"]
release_bucket = os.environ.get("STATARENA_PAYLOAD_RELEASE_BUCKET")
public_ip = urllib.request.urlopen("https://checkip.amazonaws.com", timeout=15).read().decode().strip()
print(json.dumps({"event": "network", "public_ip": public_ip}), flush=True)
for attempt in range(36):
    try:
        control = psycopg.connect(**db_config)
        break
    except psycopg.OperationalError:
        if attempt == 35:
            raise
        time.sleep(10)
catalog = {path: (size, bytes(sha), etag, content_type) for path, size, sha, etag, content_type
           in control.execute("select path,size,sha256,etag,content_type from statarena.objects").fetchall()}
existing = {(namespace, path): (size, bytes(sha), (etag or "").strip('"'))
            for namespace, path, size, sha, etag in control.execute(
                "select namespace,path,size,sha256,source_etag from statarena.file_payloads").fetchall()}
s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-2"),
                  config=Config(max_pool_connections=args.workers, retries={"max_attempts": 5}))
inventory = []
for bucket in [data_bucket] + ([release_bucket] if release_bucket and not args.data_prefix else []):
    listing = {"Bucket": bucket}
    if args.data_prefix:
        listing["Prefix"] = "data/" + args.data_prefix
    for page in s3.get_paginator("list_objects_v2").paginate(**listing):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            namespace = "data" if bucket == data_bucket and key.startswith("data/") else (
                "migration" if bucket == data_bucket else "release")
            path = key[5:] if namespace == "data" else key
            inventory.append((bucket, key, namespace, path, obj["Size"], obj["ETag"].strip('"')))
if args.limit:
    inventory = inventory[:args.limit]

pending = []
present = 0
for item in inventory:
    _, _, namespace, path, size, etag = item
    prior = existing.get((namespace, path))
    record = catalog.get(path) if namespace == "data" else None
    same = bool(prior and prior[0] == size and prior[2] == etag and (not record or prior[1] == record[1]))
    if same:
        present += 1
    else:
        pending.append(item)
print(json.dumps({"event": "inventory", "source_files": len(inventory), "already_verified": present,
                  "remaining": len(pending), "source_bytes": sum(item[4] for item in inventory)}), flush=True)

local = threading.local()
connections = []
connection_lock = threading.Lock()


def worker(item):
    bucket, key, namespace, path, size, etag = item
    if not getattr(local, "db", None):
        local.db = psycopg.connect(**db_config)
        with connection_lock:
            connections.append(local.db)
    response = s3.get_object(Bucket=bucket, Key=key, IfMatch='"' + etag + '"')
    stream = response["Body"]
    try:
        metadata = {name: response[name] for name in ("CacheControl", "ContentEncoding", "ContentDisposition", "ContentLanguage", "Metadata")
                    if response.get(name)}
        with local.db.transaction():
            lock_payload(local.db, namespace, path)
            expected_sha = None
            content_type = response.get("ContentType", "application/octet-stream")
            if namespace == "data" and path in catalog:
                current = local.db.execute("select size,sha256,content_type from statarena.objects where path=%s for update", (path,)).fetchone()
                if not current or current[0] != size or bytes(current[1]) != catalog[path][1]:
                    raise ValueError("Catalog changed during backfill")
                expected_sha = bytes(current[1])
                content_type = current[2]
            write_payload(local.db, namespace, path, stream, size, expected_sha, content_type, etag, metadata)
    finally:
        stream.close()
    return size


report = {"source_files": len(inventory), "already_verified": present, "copied": 0, "failed": 0,
          "copied_bytes": 0, "failures": []}
iterator = iter(pending)
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        active = {}
        next_progress = 1000
        while True:
            while len(active) < args.workers * 2:
                try:
                    item = next(iterator)
                except StopIteration:
                    break
                active[pool.submit(worker, item)] = (item[2], item[3])
            if not active:
                break
            done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                namespace, path = active.pop(future)
                try:
                    report["copied_bytes"] += future.result()
                    report["copied"] += 1
                except Exception as error:
                    report["failed"] += 1
                    if len(report["failures"]) < 50:
                        report["failures"].append({"namespace": namespace, "path": path, "error": type(error).__name__})
            completed = report["copied"] + report["failed"]
            if completed >= next_progress:
                print(json.dumps({key: value for key, value in report.items() if key != "failures"}), flush=True)
                next_progress = completed + 1000
finally:
    control.close()
    for connection in connections:
        connection.close()
print(json.dumps(report), flush=True)
if report["failed"]:
    raise SystemExit("Some files need another verified pass")
