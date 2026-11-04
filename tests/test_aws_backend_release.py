import importlib.util
from pathlib import Path
import sys
import unittest


RELEASE_DIR = Path(__file__).resolve().parents[1] / "infra" / "aws-backend"
sys.path.insert(0, str(RELEASE_DIR))
spec = importlib.util.spec_from_file_location("statarena_aws_release", RELEASE_DIR / "release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class SqlOnlyReleaseParameterTest(unittest.TestCase):
    def test_existing_mode_is_preserved(self):
        existing = {"Parameters": [{"ParameterKey": "SqlOnly", "ParameterValue": "1"}]}
        self.assertEqual(release.sql_only_parameter(existing, None),
                         {"ParameterKey": "SqlOnly", "UsePreviousValue": True})

    def test_new_parameter_defaults_to_legacy_mode(self):
        self.assertEqual(release.sql_only_parameter({"Parameters": []}, None),
                         {"ParameterKey": "SqlOnly", "ParameterValue": "0"})
        self.assertEqual(release.sql_only_parameter(None, None),
                         {"ParameterKey": "SqlOnly", "ParameterValue": "0"})

    def test_explicit_mode_overrides_previous_value(self):
        existing = {"Parameters": [{"ParameterKey": "SqlOnly", "ParameterValue": "0"}]}
        self.assertEqual(release.sql_only_parameter(existing, "1"),
                         {"ParameterKey": "SqlOnly", "ParameterValue": "1"})


if __name__ == "__main__":
    unittest.main()
