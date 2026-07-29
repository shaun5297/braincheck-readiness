import math
import unittest

from braincheck.features.eeg import extract
from braincheck.features.fnirs import extract as extract_fnirs


class FeatureTests(unittest.TestCase):
    def test_eeg_alpha_power_is_computed(self) -> None:
        sample_rate = 100
        samples = [
            [math.sin(2 * math.pi * 10 * index / sample_rate), math.sin(2 * math.pi * 10 * index / sample_rate)]
            for index in range(200)
        ]
        result = extract(samples, sample_rate)
        self.assertGreater(result["alpha_relative"], 0.9)
        self.assertEqual(result["valid_window_ratio"], 1.0)

    def test_fnirs_uses_optical_trend_language(self) -> None:
        result = extract_fnirs([[1.0, 2.0], [1.1, 2.1]], [[1.2, 2.2], [1.3, 2.3]])
        self.assertIn("optical_response_change", result)
        self.assertNotIn("hbo", result)


if __name__ == "__main__":
    unittest.main()

