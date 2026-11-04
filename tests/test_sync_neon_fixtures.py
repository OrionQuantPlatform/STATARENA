import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard/scripts"))
from sync_neon_fixtures import compare_fixtures


class FixtureComparisonTest(unittest.TestCase):
    def test_syncs_missing_and_newer_source_only(self):
        source = {"missing": (5, "a"), "source-newer": (5, "b"),
                  "aws-newer": (2, "c"), "equal-time-conflict": (3, "d"),
                  "equal": (1, "same")}
        target = {"source-newer": (4, "old"), "aws-newer": (6, "new"),
                  "equal-time-conflict": (3, "different"), "equal": (1, "same"),
                  "aws-only": (1, "a")}
        counts, candidates = compare_fixtures(source, target)
        self.assertEqual(candidates, ["missing", "source-newer"])
        self.assertEqual(counts, {"missing_on_aws": 1, "newer_on_neon": 1,
                                  "newer_on_aws": 1, "conflicting_equal_timestamps": 1,
                                  "available_to_sync": 2})


if __name__ == "__main__":
    unittest.main()
