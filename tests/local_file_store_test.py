import base64
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard" / "scripts"))
from file_object_store import FileObjectStore
from copy_neon_files_to_disk import copy_one


class Source:
    def __init__(self, data):
        self.data = data
        self.requests = 0

    def get_object(self, Bucket, Key):
        self.requests += 1
        return {"Body": io.BytesIO(self.data)}


class LocalFileStoreTest(unittest.TestCase):
    def test_writes_original_path_and_reads_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileObjectStore(directory)
            body = b"football data"
            expected_md5 = base64.b64encode(hashlib.md5(body).digest()).decode()
            result = store.put_object(Bucket="unused", Key="data/raw/season/a.json", Body=body, ContentMD5=expected_md5)
            self.assertEqual(Path(directory, "data/raw/season/a.json").read_bytes(), body)
            self.assertEqual(store.get_object(Bucket="unused", Key="data/raw/season/a.json")["Body"].read(), body)
            self.assertEqual(result["ETag"], '"' + hashlib.md5(body).hexdigest() + '"')

    def test_rejects_escaping_paths_and_bad_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileObjectStore(directory)
            with self.assertRaises(ValueError):
                store.put_object(Bucket="unused", Key="data/../other", Body=b"x")
            with self.assertRaises(ValueError):
                store.put_object(Bucket="unused", Key="data/raw/a", Body=b"x", ContentMD5=base64.b64encode(b"wrong").decode())
            self.assertFalse(Path(directory, "data/raw/a").exists())

    def test_copy_verifies_bytes_and_resumes_without_another_download(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileObjectStore(directory)
            body = b"original file"
            source = Source(body)
            row = ("raw/season/a.json", len(body), hashlib.sha256(body).digest())
            self.assertEqual(copy_one(source, store, "source", row), ("copied", len(body)))
            self.assertEqual(copy_one(source, store, "source", row), ("already_present", len(body)))
            self.assertEqual(source.requests, 1)
            self.assertEqual(Path(directory, "data/raw/season/a.json").read_bytes(), body)

    def test_invalid_source_cannot_replace_an_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileObjectStore(directory)
            store.put_object(Bucket="unused", Key="data/raw/a.json", Body=b"keep")
            body = b"expected"
            row = ("raw/a.json", len(body), hashlib.sha256(body).digest())
            with self.assertRaises(ValueError):
                copy_one(Source(b"incorrect"), store, "source", row)
            self.assertEqual(Path(directory, "data/raw/a.json").read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
