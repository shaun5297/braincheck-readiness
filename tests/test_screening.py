import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from braincheck.workflow.screening import ScreeningService, demo_payload


class ScreeningTests(unittest.TestCase):
    def test_result_persists_versions_and_safety_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features, quality = demo_payload("normal")
            result = ScreeningService(root).assess("A001", features, quality)
            result_path = next(root.rglob("result.json"))
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["algorithm_version"], "pilot_rules_v2")
            self.assertFalse(payload["validated_for_employment_decisions"])
            self.assertEqual(result.status, "normal")

    def test_quality_failure_outputs_unable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            features, quality = demo_payload("unable")
            result = ScreeningService(Path(directory)).assess("A001", features, quality)
            self.assertEqual(result.status, "unable")

    def test_next_sequence_avoids_overwriting_same_day_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = ScreeningService(root)
            now = datetime(2026, 8, 19, 12, 0, 0)
            target = root / "assessments" / "2026-08-19" / "BC-20260819-A001-001"
            target.mkdir(parents=True)
            self.assertEqual(service.next_sequence("A001", now=now), 2)


if __name__ == "__main__":
    unittest.main()
