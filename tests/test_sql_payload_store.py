import hashlib
import io
import json
import os
import sys
import unittest
import uuid
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard/scripts"))
from sql_payload_store import INLINE_LIMIT, read_payload, write_bytes, write_payload
from neon_store import Store
from neon_assets import save_asset_batch


@unittest.skipUnless(os.environ.get("STATARENA_RDS_TEST") == "1", "requires the AWS test database")
class SqlPayloadStoreIntegrationTest(unittest.TestCase):
    def test_exact_bytes_versions_chunks_and_rollback(self):
        credentials = json.loads(Path(os.environ["STATARENA_RDS_TEST_CREDENTIAL_FILE"]).read_text())
        db = psycopg.connect(host=os.environ["STATARENA_RDS_TEST_HOST"], dbname=os.environ["STATARENA_RDS_TEST_DATABASE"],
                             user="statarena_ingest", password=credentials["statarena_ingest"], autocommit=True,
                             sslmode="verify-full", sslrootcert=os.environ["STATARENA_RDS_TEST_CA"])
        path = "test/" + uuid.uuid4().hex

        class Rollback(Exception):
            pass

        try:
            with self.assertRaises(Rollback):
                with db.transaction():
                    for body in (b"", b"original image bytes", b"x" * (INLINE_LIMIT + 123), b"replacement"):
                        write_bytes(db, "test", path, body, "application/octet-stream")
                        self.assertEqual(read_payload(db, "test", path, hashlib.sha256(body).digest()), body)
                    self.assertEqual(db.execute("select count(*) from statarena.file_payload_chunks where namespace='test' and path=%s", (path,)).fetchone()[0], 0)
                    with self.assertRaises(ValueError):
                        write_payload(db, "test", path, io.BytesIO(b"different"), 9, bytes(32))
                    self.assertEqual(read_payload(db, "test", path), b"replacement")
                    large = b"abcdefgh" * (INLINE_LIMIT // 8 + 8)
                    write_bytes(db, "test", path, large)
                    db.execute("update statarena.file_payload_chunks set body=%s where namespace='test' and path=%s and chunk_index=0", (b"corrupt", path))
                    with self.assertRaises(ValueError):
                        read_payload(db, "test", path)
                    raise Rollback()
            self.assertIsNone(db.execute("select 1 from statarena.file_payloads where namespace='test' and path=%s", (path,)).fetchone())
        finally:
            db.close()

    def test_sql_only_ingestion_updates_catalog_bytes_and_documents(self):
        credentials = json.loads(Path(os.environ["STATARENA_RDS_TEST_CREDENTIAL_FILE"]).read_text())
        db = psycopg.connect(host=os.environ["STATARENA_RDS_TEST_HOST"], dbname=os.environ["STATARENA_RDS_TEST_DATABASE"],
                             user="statarena_ingest", password=credentials["statarena_ingest"], autocommit=True,
                             sslmode="verify-full", sslrootcert=os.environ["STATARENA_RDS_TEST_CA"])
        store = Store.__new__(Store)
        store.db, store.sql_only, store.s3 = db, True, None
        token = uuid.uuid4().hex
        path = "computed/matchdays/sql-test-" + token + ".json"
        first = ('{"version":1,"test":"' + token + '"}').encode()
        second = ('{"version":2,"test":"' + token + '"}').encode()

        class Rollback(Exception):
            pass

        try:
            with self.assertRaises(Rollback):
                with db.transaction():
                    self.assertTrue(store.put(path, first))
                    self.assertEqual(store.bytes(path), first)
                    self.assertFalse(store.put(path, first))
                    db.execute("delete from statarena.file_payloads where namespace='data' and path=%s", (path,))
                    self.assertTrue(store.put(path, first))
                    self.assertTrue(store.put(path, second))
                    self.assertEqual(store.bytes(path), second)
                    old_path = "raw/neon/versions/" + hashlib.sha256(first).hexdigest() + ".json"
                    self.assertEqual(store.bytes(old_path), first)
                    self.assertEqual(db.execute("select document->>'version' from statarena.current_file_documents where source_path=%s", (path,)).fetchone(), ("2",))
                    json_path = "raw/testing/sql-test-" + token + ".json"
                    self.assertTrue(store.put(json_path, first))
                    self.assertEqual(store.json(json_path), {"version": 1, "test": token})
                    self.assertFalse(store.put(json_path, first))
                    self.assertIsNone(db.execute("select 1 from statarena.file_payloads where namespace='data' and path=%s", (json_path,)).fetchone())
                    bad_path = "raw/testing/invalid-" + token + ".json"
                    bad = b"{invalid json"
                    self.assertTrue(store.put(bad_path, bad))
                    self.assertEqual(store.bytes(bad_path), bad)
                    self.assertEqual(db.execute("select error_count from statarena.file_document_sources where source_path=%s", (bad_path,)).fetchone(), (1,))
                    raise Rollback()
            self.assertIsNone(db.execute("select 1 from statarena.objects where path=%s", (path,)).fetchone())
        finally:
            db.close()

    def test_sql_only_image_batch_preserves_exact_bytes_without_s3(self):
        credentials = json.loads(Path(os.environ["STATARENA_RDS_TEST_CREDENTIAL_FILE"]).read_text())
        db = psycopg.connect(host=os.environ["STATARENA_RDS_TEST_HOST"], dbname=os.environ["STATARENA_RDS_TEST_DATABASE"],
                             user="statarena_ingest", password=credentials["statarena_ingest"], autocommit=True,
                             sslmode="verify-full", sslrootcert=os.environ["STATARENA_RDS_TEST_CA"])
        store = Store.__new__(Store)
        store.db, store.sql_only, store.s3 = db, True, None
        body = ("image-test-" + uuid.uuid4().hex).encode()
        sha = hashlib.sha256(body).digest()
        path = "raw/neon/assets/" + sha.hex() + ".webp"
        url = "https://cdn.pitchapi.dev/images/" + uuid.uuid4().hex + ".webp"
        row = (url, path, len(body), sha, hashlib.md5(body).hexdigest(), "image/webp", body, None)

        class Rollback(Exception):
            pass

        try:
            with self.assertRaises(Rollback):
                with db.transaction():
                    self.assertEqual(save_asset_batch(store, [row])[:3], (1, 0, len(body)))
                    self.assertEqual(read_payload(db, "data", path, sha), body)
                    self.assertEqual(db.execute("select path from statarena.assets where url=%s", (url,)).fetchone(), (path,))
                    raise Rollback()
            self.assertIsNone(db.execute("select 1 from statarena.objects where path=%s", (path,)).fetchone())
        finally:
            db.close()

    def test_existing_external_image_batch_still_publishes_metadata(self):
        credentials = json.loads(Path(os.environ["STATARENA_RDS_TEST_CREDENTIAL_FILE"]).read_text())
        db = psycopg.connect(host=os.environ["STATARENA_RDS_TEST_HOST"], dbname=os.environ["STATARENA_RDS_TEST_DATABASE"],
                             user="statarena_ingest", password=credentials["statarena_ingest"], autocommit=True,
                             sslmode="verify-full", sslrootcert=os.environ["STATARENA_RDS_TEST_CA"])
        store = Store.__new__(Store)
        store.db, store.sql_only = db, False
        body = ("external-image-test-" + uuid.uuid4().hex).encode()
        sha = hashlib.sha256(body).digest()
        path = "raw/neon/assets/" + sha.hex() + ".webp"
        url = "https://cdn.pitchapi.dev/images/" + uuid.uuid4().hex + ".webp"
        row = (url, path, len(body), sha, hashlib.md5(body).hexdigest(), "image/webp", None, None)

        class Rollback(Exception):
            pass

        try:
            with self.assertRaises(Rollback):
                with db.transaction():
                    self.assertEqual(save_asset_batch(store, [row])[:3], (1, 0, len(body)))
                    self.assertEqual(db.execute("select path from statarena.assets where url=%s", (url,)).fetchone(), (path,))
                    self.assertIsNone(db.execute("select 1 from statarena.file_payloads where namespace='data' and path=%s", (path,)).fetchone())
                    raise Rollback()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
