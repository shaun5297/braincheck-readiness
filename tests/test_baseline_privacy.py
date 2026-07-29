import unittest

from braincheck.baseline.enrollment import enroll
from braincheck.inference.result import AssessmentResult
from braincheck.privacy.access import Role, project


class BaselinePrivacyTests(unittest.TestCase):
    def test_baseline_requires_multiple_sessions(self) -> None:
        with self.assertRaises(ValueError):
            enroll("A001", [{"median_rt_s": 0.4}], [{"theta_relative": 0.2}])

    def test_supervisor_projection_hides_reasons_and_raw_features(self) -> None:
        result = AssessmentResult("BC-1", "A001", "normal", 0.8, "good", (), (), "pilot_rules_v2")
        payload = project({**result.to_dict(), "eeg": {"raw": [1]}}, Role.SUPERVISOR)
        self.assertNotIn("eeg", payload)
        self.assertNotIn("reason_codes", payload)


if __name__ == "__main__":
    unittest.main()

