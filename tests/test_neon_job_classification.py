import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard/scripts"))
from stage_neon_jobs import classify


class NeonJobClassificationTest(unittest.TestCase):
    def test_shared_differences_are_only_staged_when_requested(self):
        live = {("same", "{}"): "a", ("changed", "{}"): "old"}
        staged = {("saved", "{}")}
        self.assertEqual(classify(("new", "{}"), "x", live, staged, True), "source_only")
        self.assertIsNone(classify(("saved", "{}"), "x", live, staged, True))
        self.assertIsNone(classify(("same", "{}"), "a", live, staged, True))
        self.assertIsNone(classify(("changed", "{}"), "new", live, staged, False))
        self.assertEqual(classify(("changed", "{}"), "new", live, staged, True), "shared_conflict")


if __name__ == "__main__":
    unittest.main()
