"""Audit archive members against SQL documents without copying or deleting archives."""
import argparse
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import threading
import zipfile

import boto3
import psycopg
from botocore.config import Config
from sql_document_parser import iter_documents


# Every accepted member yields exactly one SQL document. Other members require
# a separate review rather than being silently skipped by the document parser.
SIMPLE_SUFFIXES = (".json", ".json.gz", ".csv", ".csv.gz", ".txt", ".md", ".html")


def inspect_archive(path, body):
    regular = special = unsupported = 0
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                kind = stat.S_IFMT(member.external_attr >> 16)
                if kind not in (0, stat.S_IFREG):
                    special += 1
                    continue
                regular += 1
                unsupported += not member.filename.lower().endswith(SIMPLE_SUFFIXES)
    else:
        with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile():
                    special += 1
                    continue
                regular += 1
                unsupported += not member.name.lower().endswith(SIMPLE_SUFFIXES)
    records = list(iter_documents(path, body)) if not (special or unsupported) else []
    errors = sum(record[3] is not None for record in records)
    return {"regular_members": regular, "special_members": special,
            "unsupported_members": unsupported, "parsed_documents": len(records),
            "parse_errors": errors}, records


def compare_documents(db, path, digest, records):
    source = db.execute("""SELECT status,document_count,error_count FROM statarena.file_document_sources
        WHERE source_path=%s AND source_sha256=%s""", (path, digest)).fetchone()
    if not source or source != ("ready", len(records), 0):
        return max(1, len(records))
    actual = db.execute("""SELECT count(*) FROM statarena.file_documents
        WHERE source_path=%s AND source_sha256=%s AND error IS NULL""", (path, digest)).fetchone()[0]
    mismatch = abs(actual - len(records))
    for offset in range(0, len(records), 50):
        batch = [{"path": doc_path, "format": kind, "doc_text": text}
                 for doc_path, kind, text, error in records[offset:offset + 50] if error is None]
        payload = json.dumps(batch, ensure_ascii=False, separators=(",", ":"))
        mismatch += db.execute("""SELECT count(*) FROM jsonb_to_recordset(%s::jsonb)
            AS expected(path text,format text,doc_text text)
            LEFT JOIN statarena.file_documents actual ON actual.document_path=expected.path
              AND actual.source_path=%s AND actual.source_sha256=%s
            WHERE actual.document_path IS NULL OR actual.error IS NOT NULL
              OR actual.format IS DISTINCT FROM expected.format
              OR actual.document IS DISTINCT FROM expected.doc_text::jsonb""", (payload, path, digest)).fetchone()[0]
    return mismatch


def audit_one(db, s3, bucket, row, persist=False):
    path, size, digest, etag = row
    digest = bytes(digest)
    response = s3.get_object(Bucket=bucket, Key="data/" + path, IfMatch='"' + etag.strip('"') + '"')
    try:
        body = response["Body"].read()
    finally:
        response["Body"].close()
    if len(body) != size or hashlib.sha256(body).digest() != digest:
        raise ValueError("Archive no longer matches its catalog checksum")
    report, records = inspect_archive(path, body)
    mismatch = 0
    if not (report["special_members"] or report["unsupported_members"] or report["parse_errors"]):
        if report["regular_members"] != report["parsed_documents"]:
            mismatch = 1
        else:
            mismatch = compare_documents(db, path, digest, records)
    report["document_mismatches"] = mismatch
    report["status"] = ("verified" if not (report["special_members"] or report["unsupported_members"]
                        or report["parse_errors"] or mismatch) else "needs_review")
    if persist:
        result = db.execute("""INSERT INTO statarena.archive_audits
            (path,source_sha256,status,regular_members,special_members,unsupported_members,
             parsed_documents,parse_errors,document_mismatches)
            SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s FROM statarena.objects
            WHERE path=%s AND sha256=%s
            ON CONFLICT(path,source_sha256) DO UPDATE SET status=excluded.status,
              regular_members=excluded.regular_members,special_members=excluded.special_members,
              unsupported_members=excluded.unsupported_members,parsed_documents=excluded.parsed_documents,
              parse_errors=excluded.parse_errors,document_mismatches=excluded.document_mismatches,audited_at=now()
            RETURNING path""", (path, digest, report["status"], report["regular_members"],
             report["special_members"], report["unsupported_members"], report["parsed_documents"],
             report["parse_errors"], mismatch, path, digest)).fetchone()
        if not result:
            raise ValueError("Archive catalog changed during the audit")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "apply"))
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--retry-needs-review", action="store_true",
                        help="recheck versions previously marked as needing review")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4 or (args.limit is not None and args.limit < 1):
        raise ValueError("Invalid worker count or limit")
    url = os.environ["STATARENA_TARGET_DATABASE_URL"]
    control = psycopg.connect(url, autocommit=True, connect_timeout=20)
    if args.mode == "apply":
        migration = Path(__file__).resolve().parents[1] / "backend/migrations/017_archive_audits.sql"
        control.execute(migration.read_text())
    existing = bool(control.execute("SELECT to_regclass('statarena.archive_audits')").fetchone()[0])
    only_verified = " AND a.status='verified'" if args.retry_needs_review else ""
    excluded = ("AND NOT EXISTS(SELECT 1 FROM statarena.archive_audits a "
                "WHERE a.path=o.path AND a.source_sha256=o.sha256" + only_verified + ")"
                if existing and args.mode == "apply" else "")
    rows = control.execute("""SELECT o.path,o.size,o.sha256,o.etag FROM statarena.objects o
        WHERE o.path LIKE %s AND (lower(o.path) LIKE '%%.tar.gz' OR lower(o.path) LIKE '%%.tgz'
        OR lower(o.path) LIKE '%%.zip') """ + excluded + " ORDER BY o.size DESC LIMIT %s",
        (args.prefix + "%", args.limit)).fetchall()
    control.close()
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-2"),
                      config=Config(max_pool_connections=args.workers, retries={"max_attempts": 4}))
    local = threading.local()
    connections = []
    lock = threading.Lock()

    def worker(row):
        if not getattr(local, "db", None):
            local.db = psycopg.connect(url, autocommit=True, connect_timeout=20)
            with lock:
                connections.append(local.db)
        return audit_one(local.db, s3, args.bucket, row, args.mode == "apply")

    summary = {"archives": len(rows), "verified": 0, "needs_review": 0, "failed": 0, "failures": []}
    iterator = iter(rows)
    next_progress = 25
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            active = {}
            while True:
                while len(active) < args.workers * 2:
                    try:
                        row = next(iterator)
                    except StopIteration:
                        break
                    active[pool.submit(worker, row)] = row[0]
                if not active:
                    break
                done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    path = active.pop(future)
                    try:
                        summary[future.result()["status"]] += 1
                    except Exception as error:
                        summary["failed"] += 1
                        if len(summary["failures"]) < 20:
                            summary["failures"].append({"path": path, "error": type(error).__name__})
                    completed = summary["verified"] + summary["needs_review"] + summary["failed"]
                    if completed >= next_progress:
                        print(json.dumps({key: value for key, value in summary.items() if key != "failures"}), flush=True)
                        next_progress = completed + 25
    finally:
        for connection in connections:
            connection.close()
    print(json.dumps(summary), flush=True)
    if summary["failed"]:
        raise SystemExit("Archive audit stopped; rerun to process unrecorded versions")


if __name__ == "__main__":
    main()
