"""Small object-store adapter backed by the existing data/ directory."""

import base64
import hashlib
import io
import os
import tempfile
from pathlib import Path


class FileObjectStore:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)

    def _path(self, key):
        if not key.startswith("data/") or any(part in ("", ".", "..") for part in key.split("/")):
            raise ValueError("Invalid file key")
        result = (self.root / key).resolve()
        if not result.is_relative_to((self.root / "data").resolve()):
            raise ValueError("File key escapes data directory")
        return result

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self._path(Key).read_bytes())}

    def head_object(self, Bucket, Key):
        body = self._path(Key).read_bytes()
        return {"ContentLength": len(body), "ETag": '"' + hashlib.md5(body).hexdigest() + '"'}

    def put_object(self, Bucket, Key, Body, ContentMD5=None, **_):
        body = bytes(Body)
        digest = hashlib.md5(body).digest()
        if ContentMD5 is not None and base64.b64decode(ContentMD5) != digest:
            raise ValueError("File MD5 mismatch")
        target = self._path(Key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temporary = handle.name
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return {"ETag": '"' + digest.hex() + '"'}

    def put_verified_stream(self, Key, source, expected_size, expected_sha256):
        """Write a source object atomically only if every byte matches its catalog."""
        target = self._path(Key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        digest = hashlib.sha256()
        size = 0
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temporary = handle.name
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                if size != expected_size or digest.digest() != expected_sha256:
                    raise ValueError("Source file does not match its catalog")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
