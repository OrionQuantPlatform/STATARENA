import io
from pathlib import Path
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard/scripts"))
from audit_s3_archives import inspect_archive


def make_archive(files, symlink=False):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, body in files:
            item = tarfile.TarInfo(name)
            item.size = len(body)
            archive.addfile(item, io.BytesIO(body))
        if symlink:
            item = tarfile.TarInfo("link")
            item.type = tarfile.SYMTYPE
            item.linkname = "club.json"
            archive.addfile(item)
    return output.getvalue()


class ArchiveAuditTest(unittest.TestCase):
    def test_supported_members_and_duplicate_paths_are_all_parsed(self):
        body = make_archive([("club.json", b'{"id":1}'), ("club.json", b'{"id":2}'),
                             ("table.csv", b"name,points\nCaen,3\n"), ("readme.md", b"source")])
        counts, docs = inspect_archive("sources/test.tar.gz", body)
        self.assertEqual(counts, {"regular_members": 4, "special_members": 0,
                                  "unsupported_members": 0, "parsed_documents": 4, "parse_errors": 0})
        self.assertEqual(len({row[0] for row in docs}), 4)
        self.assertTrue(any("duplicate-2/" in row[0] for row in docs))

    def test_unknown_or_special_members_require_review(self):
        for body in (make_archive([("logo.webp", b"bytes")]),
                     make_archive([("club.json", b"{}")], symlink=True)):
            counts, docs = inspect_archive("sources/test.tar.gz", body)
            self.assertTrue(counts["unsupported_members"] or counts["special_members"])
            self.assertEqual(docs, [])


if __name__ == "__main__":
    unittest.main()
