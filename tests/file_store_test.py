import hashlib
import io
import contextlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard" / "scripts"))
from neon_store import Store
from botocore.exceptions import ClientError
import prune_inline_file_copies


class Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class Database:
    def __init__(self):
        self.rows = {}
        self.last_insert = None

    def execute(self, sql, values):
        if sql.startswith("select sha256,size"):
            return Result(self.rows.get(values[0]))
        if sql.startswith("select sha256"):
            row = self.rows.get(values[0])
            return Result((row[0],) if row else None)
        if sql.startswith("insert into statarena.objects"):
            self.last_insert = values
            self.rows[values[0]] = (values[2], values[1])
            return Result(None)
        raise AssertionError(sql)


class Objects:
    def __init__(self):
        self.files = {}
        self.reads = 0

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.files[Key] = Body
        return {"ETag": '"' + hashlib.md5(Body).hexdigest() + '"'}

    def get_object(self, Bucket, Key):
        self.reads += 1
        if Key not in self.files:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.files[Key])}


class FileStoreTest(unittest.TestCase):
    def setUp(self):
        self.store = Store.__new__(Store)
        self.store.db = Database()
        self.store.s3 = Objects()
        self.store.bucket = "test"

    def test_hot_file_is_not_duplicated_in_sql(self):
        body = b'{"example":true}'
        self.store.put("raw/example.json", body, hot=True)
        self.assertIsNone(self.store.db.last_insert[4])
        self.assertEqual(self.store.bytes("raw/example.json"), body)
        self.assertEqual(self.store.s3.reads, 1)

    def test_file_integrity_is_checked_when_read(self):
        self.store.put("raw/example.json", b"original")
        self.store.s3.files["data/raw/example.json"] = b"different"
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.store.bytes("raw/example.json")

    def test_interrupted_manifest_write_uses_verified_previous_version(self):
        body = b"previous"
        self.store.put("raw/index.json", body)
        digest = hashlib.sha256(body).hexdigest()
        self.store.s3.files["data/raw/neon/versions/" + digest + ".json"] = body
        self.store.s3.files["data/raw/index.json"] = b"uncommitted"
        self.assertEqual(self.store.bytes("raw/index.json"), body)

    def test_put_repairs_missing_file_even_when_metadata_has_same_digest(self):
        body = b"original"
        self.store.put("raw/example.json", body)
        del self.store.s3.files["data/raw/example.json"]
        self.assertTrue(self.store.put("raw/example.json", body, hot=True))
        self.assertEqual(self.store.bytes("raw/example.json"), body)
        self.assertIsNone(self.store.db.last_insert[4])


class PruneDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.updated = []

    def execute(self, sql, values=None):
        if "pg_try_advisory_lock" in sql:
            return Result((True,))
        if sql.startswith("select path,size,sha256,body"):
            result = Result(None)
            result.fetchall = lambda: self.rows
            return result
        if sql.startswith("update statarena.objects"):
            self.updated.append(values[0])
            result = Result(None)
            result.rowcount = 1
            return result
        if "pg_advisory_unlock" in sql:
            return Result((True,))
        raise AssertionError(sql)

    def transaction(self):
        return contextlib.nullcontext()

    def close(self):
        pass


class PruneTest(unittest.TestCase):
    def test_all_files_are_verified_before_any_sql_copy_is_removed(self):
        first, second = b"first", b"second"
        rows = [
            ("raw/first.json", len(first), hashlib.sha256(first).digest(), first),
            ("raw/second.json", len(second), hashlib.sha256(second).digest(), second),
        ]
        store = Store.__new__(Store)
        store.db = PruneDatabase(rows)
        store.s3 = Objects()
        store.bucket = "test"
        store.s3.files = {
            "data/raw/first.json": first,
            "data/raw/second.json": b"corrupted",
        }
        with patch.object(prune_inline_file_copies, "Store", return_value=store):
            with patch.object(sys, "argv", ["prune_inline_file_copies.py", "--apply"]):
                with self.assertRaisesRegex(ValueError, "Stored file does not match"):
                    prune_inline_file_copies.main()
        self.assertEqual(store.db.updated, [])


if __name__ == "__main__":
    unittest.main()
