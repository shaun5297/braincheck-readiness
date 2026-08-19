import math
import tempfile
import unittest
from pathlib import Path

from braincheck.acquisition.live_streams import LiveBuffer
from braincheck.workflow.live_screening import LiveScreeningSession
from braincheck.workflow.screening import ScreeningService, demo_payload


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class _Marker:
    def __init__(self, _path: Path) -> None:
        self.rows: list[tuple[str, dict[str, object], float]] = []
        self.closed = False

    def push(self, event: str, payload: dict[str, object], timestamp: float) -> None:
        self.rows.append((event, payload, timestamp))

    def close(self) -> None:
        self.closed = True


class _Recorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.started = False
        self.stopped = False

    def start(self, timeout: float = 5.0) -> None:
        self.path.write_bytes(b"XDF:test")
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def nominal_srate(self, kind: str) -> float:
        return 100.0 if kind == "eeg" else 25.0

    def samples_between(self, kind: str, start: float, end: float):
        count = 200 if kind == "eeg" else 100
        rate = self.nominal_srate(kind)
        timestamps = tuple(start + index / rate for index in range(count))
        if kind == "eeg":
            samples = tuple(
                (
                    math.sin(2 * math.pi * 10 * index / rate),
                    math.sin(2 * math.pi * 10 * index / rate),
                )
                for index in range(count)
            )
        elif kind == "fnirs":
            samples = tuple((1.0 + index * 0.001,) * 4 for index in range(count))
        else:
            samples = tuple((0.01 * math.sin(index / 10),) * 6 for index in range(count))
        return timestamps, samples

    def summary(self):
        return {
            kind: {"sample_count": 200, "first_timestamp": 0.0, "last_timestamp": 255.0}
            for kind in ("eeg", "fnirs", "motion")
        }


class LiveScreeningTests(unittest.TestCase):
    def test_analysis_window_orders_samples_but_retains_arrival_diagnostic(self) -> None:
        buffer = LiveBuffer(1)
        buffer.append(((2.0,), (1.0,), (3.0,)), (2.0, 1.0, 3.0))
        timestamps, samples = buffer.between(0.0, 4.0)
        self.assertEqual(timestamps, (1.0, 2.0, 3.0))
        self.assertEqual(samples, ((1.0,), (2.0,), (3.0,)))
        self.assertEqual(buffer.arrival_inversion_count, 1)

    def test_real_flow_builds_features_and_auditable_capture(self) -> None:
        clock = _Clock()
        markers: list[_Marker] = []

        def marker_factory(path: Path) -> _Marker:
            marker = _Marker(path)
            markers.append(marker)
            return marker

        with tempfile.TemporaryDirectory() as directory:
            session = LiveScreeningSession(
                Path(directory),
                "A001",
                sequence=1,
                recorder_factory=_Recorder,
                marker_factory=marker_factory,
                clock=clock,
            )
            session.start()
            session.start_phase("quality")
            clock.value = 30.0
            session.end_phase("quality")
            session.start_phase("baseline")
            clock.value = 75.0
            session.end_phase("baseline")
            session.start_phase("sart")
            for trial in range(1, 181):
                clock.value = 75.0 + trial - 1
                stimulus = "3" if trial % 9 == 0 else "1"
                onset = session.start_trial(trial=trial, stimulus=stimulus)
                response = None if stimulus == "3" else onset + 0.35
                session.record_trial(
                    trial=trial,
                    stimulus=stimulus,
                    response_time_s=None if response is None else 0.35,
                    stimulus_timestamp=onset,
                    response_timestamp=response,
                )
            clock.value = 255.0
            session.end_phase("sart")
            outcome = session.finish(
                {
                    "kss": 3,
                    "sleep_hours_24h": 8,
                    "continuous_awake_hours": 8,
                    "shift": "日班",
                    "acute_discomfort": False,
                }
            )
            self.assertTrue(outcome.quality.passed)
            self.assertEqual(outcome.features.behavior["valid_trial_count"], 180)
            self.assertEqual(outcome.features.metadata["acquisition_mode"], "live_lsl")
            self.assertTrue(outcome.raw_xdf.exists())
            self.assertTrue((outcome.capture_directory / "capture.json").exists())
            self.assertTrue(markers[0].closed)
            self.assertIn("sart_stimulus", [row[0] for row in markers[0].rows])

    def test_competition_demo_placeholder_never_bypasses_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            features, quality = demo_payload("normal")
            normal = ScreeningService(Path(directory)).assess(
                "A001",
                features,
                quality,
                competition_demo=True,
            )
            self.assertEqual(normal.status, "normal")
            self.assertEqual(normal.algorithm_version, "competition_demo_placeholder_v1")

        with tempfile.TemporaryDirectory() as directory:
            features, quality = demo_payload("unable")
            unable = ScreeningService(Path(directory)).assess(
                "A001",
                features,
                quality,
                competition_demo=True,
            )
            self.assertEqual(unable.status, "unable")
            self.assertEqual(unable.algorithm_version, "quality_gate_v1")


if __name__ == "__main__":
    unittest.main()
