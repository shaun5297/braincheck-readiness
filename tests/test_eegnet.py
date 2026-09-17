import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from braincheck.inference.eegnet import EEGNetModel, attach_prediction
from braincheck.inference.fusion import infer
from braincheck.workflow.screening import ScreeningService, demo_payload
from braincheck.quality.motion import evaluate as motion_quality


class EEGNetIntegrationTests(unittest.TestCase):
    def test_pilot_motion_relaxation_preserves_original_qc_and_other_failures(self):
        from braincheck.quality.gate import GateResult

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.manifest(root)
            m = json.loads(path.read_text())
            m.update(
                training_mode="pilot_fit_only",
                allowed_modes=["shadow", "pilot_assisted"],
                decision_threshold=None,
                pilot_decision_policy={
                    "threshold": 0.5,
                    "calibrated": False,
                    "basis": "engineering_demo_parameter",
                    "max_motion_artifact_ratio": 0.4,
                },
            )
            path.write_text(json.dumps(m))
            features, _ = demo_payload("normal")
            features.metadata["eegnet"] = {
                "status": "ok",
                "model_sha256": "fixture-sha",
                "p_impaired": 0.7,
                "window_count": 20,
            }
            service = ScreeningService(root / "data", path, "pilot_assisted")
            gate = GateResult(
                False, ("excessive_motion",), {"motion": {"artifact_window_ratio": 0.3}}
            )
            self.assertEqual(
                service.assess("T", features, gate, sequence=1).status, "retest"
            )
            self.assertFalse(
                features.metadata["effective_quality"]["metrics"][
                    "original_quality_passed"
                ]
            )
            bad = GateResult(
                False, ("excessive_motion", "lsl_stream_incomplete"), gate.metrics
            )
            self.assertEqual(
                service.assess("T", features, bad, sequence=2).status, "unable"
            )
            features.metadata["eegnet"]["window_count"] = 9
            self.assertEqual(
                service.assess("T", features, gate, sequence=3).status, "unable"
            )

    def test_pilot_engineering_threshold_routes_four_states(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.manifest(root)
            manifest = json.loads(path.read_text())
            manifest.update(
                training_mode="pilot_fit_only",
                allowed_modes=["shadow", "pilot_assisted"],
                decision_threshold=None,
                pilot_decision_policy={
                    "threshold": 0.5,
                    "calibrated": False,
                    "basis": "engineering_demo_parameter",
                },
            )
            path.write_text(json.dumps(manifest))
            service = ScreeningService(root / "data", path, "pilot_assisted")
            features, gate = demo_payload("normal")
            features.metadata["eegnet"] = {
                "status": "ok",
                "model_sha256": "fixture-sha",
                "p_impaired": 0.3,
            }
            self.assertEqual(
                service.assess("T", features, gate, sequence=1).status, "normal"
            )
            features.metadata["eegnet"]["p_impaired"] = 0.7
            first = service.assess("T", features, gate, sequence=2)
            self.assertEqual(first.status, "retest")
            self.assertIn("eegnet_pilot_evidence", first.reason_codes)
            self.assertEqual(
                service.assess(
                    "T",
                    features,
                    gate,
                    sequence=3,
                    parent_assessment_id=first.assessment_id,
                ).status,
                "rest",
            )
            _, failed = demo_payload("unable")
            self.assertEqual(
                service.assess("T", features, failed, sequence=4).status, "unable"
            )

    def test_pilot_can_log_clean_windows_without_overriding_failed_run_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.manifest(root)
            manifest = json.loads(path.read_text())
            manifest.update(
                training_mode="pilot_fit_only", quality_profile="pilot_clean_windows"
            )
            path.write_text(json.dumps(manifest))
            features, _ = demo_payload("normal")
            from braincheck.quality.gate import GateResult

            gate = GateResult(False, ("excessive_motion",), {})
            with patch("braincheck.inference.eegnet.EEGNetModel") as cls:
                cls.return_value.predict_segments.return_value = {
                    "status": "ok",
                    "p_impaired": 0.7,
                }
                attach_prediction(
                    features,
                    gate,
                    path,
                    [],
                    [],
                    [],
                    channel_names=[],
                    nominal_srate=250,
                )
            self.assertFalse(features.metadata["eegnet"]["overall_quality_passed"])
            self.assertEqual(
                ScreeningService(root / "data", path)
                .assess("T", features, gate)
                .status,
                "unable",
            )

    def test_unvalidated_pilot_never_changes_decision_even_if_assisted_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.manifest(Path(directory))
            manifest = json.loads(path.read_text())
            manifest.update(
                training_mode="pilot_fit_only",
                decision_threshold=None,
                calibration_split="none",
            )
            path.write_text(json.dumps(manifest))
            features, _ = demo_payload("normal")
            features.metadata["eegnet"] = {
                "status": "ok",
                "model_sha256": "fixture-sha",
                "p_impaired": 0.99,
            }
            result = infer(
                features, is_retest=False, model_manifest=path, eegnet_mode="assisted"
            )
            self.assertEqual(result[0], "normal")
            self.assertIn("pilot_shadow", result[3])

    def test_motion_ratio_uses_time_windows_instead_of_whole_run_boolean(self):
        times = [i / 10 for i in range(201)]
        samples = [[0.0] * 6 for _ in times]
        samples[100][3] = 10.0
        result = motion_quality(samples, timestamps=times)
        self.assertGreater(result["artifact_window_ratio"], 0)
        self.assertLess(result["artifact_window_ratio"], 1)
        self.assertEqual(result["candidate_windows"], 9)

    def manifest(self, root):
        path = root / "model_manifest.json"
        path.write_text(
            json.dumps(
                {
                    "model_type": "eegnet_torchscript",
                    "available": True,
                    "training_source": "bsense_reference_export",
                    "model_version": "fixture-only",
                    "model_sha256": "fixture-sha",
                    "calibration_split": "validation",
                    "calibration_balanced_accuracy": 0.7,
                    "decision_threshold": 0.63,
                }
            )
        )
        return path

    def test_shadow_records_model_without_changing_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.manifest(Path(directory))
            features, _ = demo_payload("normal")
            features.metadata["eegnet"] = {
                "status": "ok",
                "model_sha256": "fixture-sha",
                "p_impaired": 0.9,
            }
            result = infer(
                features, is_retest=False, model_manifest=path, eegnet_mode="shadow"
            )
            self.assertEqual(result[0], "normal")
            self.assertIn("eegnet_shadow", result[3])

    def test_validated_threshold_and_retest_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.manifest(Path(directory))
            features, _ = demo_payload("normal")
            features.metadata["eegnet"] = {
                "status": "ok",
                "model_sha256": "fixture-sha",
                "p_impaired": 0.7,
            }
            first = infer(
                features, is_retest=False, model_manifest=path, eegnet_mode="assisted"
            )
            repeat = infer(
                features, is_retest=True, model_manifest=path, eegnet_mode="assisted"
            )
            self.assertEqual(first[0], "retest")
            self.assertEqual(repeat[0], "rest")
            features.metadata["eegnet"]["p_impaired"] = 0.62
            self.assertEqual(
                infer(
                    features,
                    is_retest=False,
                    model_manifest=path,
                    eegnet_mode="assisted",
                )[0],
                "normal",
            )

    def test_model_never_overrides_failed_quality(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.manifest(root)
            features, gate = demo_payload("unable")
            with patch(
                "braincheck.inference.eegnet.EEGNetModel",
                side_effect=AssertionError("must not load"),
            ):
                attach_prediction(
                    features,
                    gate,
                    path,
                    [],
                    [],
                    [],
                    channel_names=[],
                    nominal_srate=250,
                )
            self.assertEqual(
                features.metadata["eegnet"]["status"], "skipped_quality_gate"
            )
            result = ScreeningService(root / "data", path, "assisted").assess(
                "TEST", features, gate
            )
            self.assertEqual(result.status, "unable")

    def test_wrong_artifact_and_missing_model_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.manifest(root)
            features, gate = demo_payload("normal")
            features.metadata["eegnet"] = {
                "status": "ok",
                "model_sha256": "wrong-sha",
                "p_impaired": 0.99,
            }
            self.assertEqual(
                infer(
                    features,
                    is_retest=False,
                    model_manifest=path,
                    eegnet_mode="assisted",
                )[3],
                "pilot_rules_v2",
            )
            attach_prediction(
                features,
                gate,
                root / "missing.json",
                [],
                [],
                [],
                channel_names=[],
                nominal_srate=250,
            )
            self.assertEqual(features.metadata["eegnet"]["status"], "unavailable")

    def test_synthetic_training_artifact_cannot_be_deployed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model_manifest.json"
            path.write_text(json.dumps({"training_source": "synthetic_test_fixture"}))
            with self.assertRaisesRegex(ValueError, "不是自采 reference 模型"):
                EEGNetModel(path)


if __name__ == "__main__":
    unittest.main()
