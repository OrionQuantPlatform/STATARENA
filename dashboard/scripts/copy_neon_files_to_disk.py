#!/usr/bin/env python3
"""Resume a checksum-verified copy of catalogued Neon files to data/ on disk."""

import argparse
import concurrent.futures
import hashlib
import json
import os

import boto3
import psycopg
from botocore.config import Config

from file_object_store import FileObjectStore


def copy_one(source, destination, bucket, row, verify_only=False):
    path, size, digest = row
    digest = bytes(digest)
    key = "data/" + path
    target = destination._path(key)
    if target.is_file() and target.stat().st_size == size:
        with target.open("rb") as existing:
            if hashlib.file_digest(existing, "sha256").digest() == digest:
                return "already_present", size
    if verify_only:
        raise ValueError("Local file is missing or differs from the catalog")
    remote = source.get_object(Bucket=bucket, Key=key)["Body"]
    try:
        destination.put_verified_stream(key, remote, size, digest)
    finally:
        remote.close()
    return "copied", size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True, help="Existing directory that will contain data/")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--verify-only", action="store_true", help="Read local files and compare hashes without downloading")
    args = parser.parse_args()
    if not 1 <= args.workers <= 32:
        raise ValueError("workers must be between 1 and 32")
    destination = FileObjectStore(args.destination)
    with psycopg.connect(os.environ["NEON_DATABASE_URL"], options="-c default_transaction_read_only=on") as db:
        rows = db.execute("select path,size,sha256 from statarena.objects order by path").fetchall()
    source = None if args.verify_only else boto3.client(
        "s3",
        endpoint_url=os.environ["NEON_STORAGE_ENDPOINT"],
        region_name=os.environ.get("NEON_STORAGE_REGION", "us-east-2"),
        aws_access_key_id=os.environ["NEON_STORAGE_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["NEON_STORAGE_SECRET_ACCESS_KEY"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            retries={"max_attempts": 4},
            max_pool_connections=args.workers,
        ),
    )
    bucket = os.environ.get("NEON_STORAGE_BUCKET", "statarena-data")
    result = {"objects": len(rows), "copied": 0, "already_present": 0, "failed": 0, "copied_bytes": 0, "failures": []}
    iterator = iter(rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {}
        while True:
            while len(pending) < args.workers * 2:
                try:
                    row = next(iterator)
                except StopIteration:
                    break
                pending[pool.submit(copy_one, source, destination, bucket, row, args.verify_only)] = row[0]
            if not pending:
                break
            done, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                path = pending.pop(future)
                try:
                    state, size = future.result()
                    result[state] += 1
                    if state == "copied":
                        result["copied_bytes"] += size
                except Exception as error:
                    result["failed"] += 1
                    if len(result["failures"]) < 20:
                        result["failures"].append({"path": path, "error": type(error).__name__})
            if (result["copied"] + result["already_present"] + result["failed"]) % 5000 == 0:
                print(json.dumps({k: v for k, v in result.items() if k != "failures"}), flush=True)
    print(json.dumps(result), flush=True)
    if result["failed"]:
        raise SystemExit("Verification or copy incomplete; inspect the reported failures")


if __name__ == "__main__":
    main()
