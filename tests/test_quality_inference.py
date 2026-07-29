import unittest

from braincheck.features.schema import ReadinessFeatures
from braincheck.inference.rules import infer
from braincheck.quality.gate import evaluate


def features(**context: object) -> ReadinessFeatures:
    return ReadinessFeatures(
        behavior={"omission_rate": 0.01, "commission_rate": 0.02, "rt_cv": 0.15},
        eeg={},
        fnirs={},
        context={"kss": 3, "sleep_hours_24h": 8, "continuous_awake_hours": 8, **context},
        quality={},
    )


class QualityInferenceTests(unittest.TestCase):
    def test_quality_failure_is_unable_before_inference(self) -> None:
        result = evaluate(
            {"valid_channel_ratio": 0},
            {"valid_channel_ratio": 1, "saturation_ratio": 0},
            {"artifact_window_ratio": 0},
            {"stream_complete": True, "timestamp_inversion_count": 0},
            valid_sart_trials=180,
        )
        self.assertFalse(result.passed)
        self.assertIn("eeg_quality_insufficient", result.reason_codes)

    def test_first_assessment_never_escalates_directly_to_rest(self) -> None:
        status, _, _ = infer(features(kss=9, sleep_hours_24h=3, continuous_awake_hours=24), is_retest=False)
        self.assertEqual(status, "retest")

    def test_retest_can_escalate_to_rest(self) -> None:
        status, _, _ = infer(features(kss=9, sleep_hours_24h=3), is_retest=True)
        self.assertEqual(status, "rest")


if __name__ == "__main__":
    unittest.main()

