from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..acquisition.marker_outlet import MarkerOutlet
from ..acquisition.recorder import Recorder
from ..features.behavior import classify_sart_trial
from ..features.schema import ReadinessFeatures
from ..quality.gate import GateResult
from .pipeline import ScreeningInput, process


def lsl_clock() -> float:
    from pylsl import local_clock

    return float(local_clock())


@dataclass(frozen=True)
class LiveScreeningOutcome:
    features: ReadinessFeatures
    quality: GateResult
    capture_directory: Path
    raw_xdf: Path


class LiveScreeningSession:
    """Own one real-device BrainCheck acquisition from LSL start to features."""

    def __init__(
        self,
        data_root: Path,
        participant_id: str,
        *,
        sequence: int,
        recorder_factory: Callable[[Path], Recorder] = Recorder,
        marker_factory: Callable[[Path], MarkerOutlet] = MarkerOutlet,
        clock: Callable[[], float] = lsl_clock,
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.capture_directory = data_root / "captures" / f"BC-CAP-{timestamp}-{sequence:03d}"
        self.raw_xdf = self.capture_directory / "raw.xdf"
        self.marker_audit = self.capture_directory / "markers.jsonl"
        self.context_path = self.capture_directory / "capture.json"
        self.participant_id = participant_id
        self.sequence = sequence
        self._recorder_factory = recorder_factory
        self._marker_factory = marker_factory
        self._clock = clock
        self._recorder: Recorder | None = None
        self._marker: MarkerOutlet | None = None
        self._phase_bounds: dict[str, list[float]] = {}
        self._trials: list[dict[str, object]] = []
        self._started = False
        self._finished = False

    def start(self, *, timeout: float = 5.0) -> None:
        if self._started:
            raise RuntimeError("本次采集已经启动")
        self.capture_directory.mkdir(parents=True, exist_ok=False)
        marker = self._marker_factory(self.marker_audit)
        recorder = self._recorder_factory(self.raw_xdf)
        try:
            recorder.start(timeout=timeout)
        except Exception:
            marker.close()
            self._write_context("start_failed")
            raise
        self._marker = marker
        self._recorder = recorder
        self._started = True
        self._push("screening_started", {"participant_id": self.participant_id})

    def start_phase(self, phase: str) -> float:
        self._require_recording()
        timestamp = self._clock()
        self._phase_bounds[phase] = [timestamp]
        self._push(f"{phase}_start", {}, timestamp=timestamp)
        return timestamp

    def end_phase(self, phase: str) -> float:
        self._require_recording()
        bounds = self._phase_bounds.get(phase)
        if not bounds or len(bounds) != 1:
            raise RuntimeError(f"阶段尚未开始或已经结束：{phase}")
        timestamp = self._clock()
        bounds.append(timestamp)
        self._push(f"{phase}_end", {}, timestamp=timestamp)
        return timestamp

    def record_trial(
        self,
        *,
        trial: int,
        stimulus: str,
        response_time_s: float | None,
        stimulus_timestamp: float | None = None,
        response_timestamp: float | None = None,
    ) -> dict[str, object]:
        self._require_recording()
        row = classify_sart_trial(stimulus != "3", response_time_s)
        row.update(
            {
                "trial": trial,
                "stimulus": stimulus,
                "stimulus_timestamp": stimulus_timestamp,
                "response_timestamp": response_timestamp,
            }
        )
        if response_timestamp is not None:
            self._push(
                "sart_response",
                {"trial": trial, "response_time_s": response_time_s},
                timestamp=response_timestamp,
            )
        self._trials.append(row)
        self._push("sart_trial_result", row)
        return row

    def start_trial(self, *, trial: int, stimulus: str) -> float:
        self._require_recording()
        timestamp = self._clock()
        self._push(
            "sart_stimulus",
            {"trial": trial, "stimulus": stimulus, "should_respond": stimulus != "3"},
            timestamp=timestamp,
        )
        return timestamp

    def clock_now(self) -> float:
        return self._clock()

    def finish(self, context: dict[str, object]) -> LiveScreeningOutcome:
        self._require_recording()
        for phase in ("baseline", "sart"):
            bounds = self._phase_bounds.get(phase)
            if bounds is None or len(bounds) != 2:
                raise RuntimeError(f"采集阶段不完整：{phase}")
        if len(self._trials) != 180:
            raise RuntimeError(f"SART 应完成 180 个试次，实际 {len(self._trials)}")
        self._push("screening_finished", {"trial_count": len(self._trials)})
        assert self._recorder is not None
        assert self._marker is not None
        try:
            self._recorder.stop()
        except Exception as exc:
            self._finished = True
            self._write_context("recorder_failed", context=context, extra={"failure": str(exc)})
            raise
        finally:
            self._marker.close()
        try:
            features, quality = self._build_features(context)
        except Exception as exc:
            self._finished = True
            self._write_context("processing_failed", context=context, extra={"failure": str(exc)})
            raise
        features.metadata.update(
            {
                "acquisition_mode": "live_lsl",
                "capture_directory": str(self.capture_directory),
                "raw_xdf": str(self.raw_xdf),
            }
        )
        self._finished = True
        self._write_context("completed", context=context, quality=quality.to_dict())
        return LiveScreeningOutcome(features, quality, self.capture_directory, self.raw_xdf)

    def abort(self, reason: str) -> None:
        if not self._started or self._finished:
            return
        if self._marker is not None:
            try:
                self._push("screening_aborted", {"reason": reason})
            except Exception:
                pass
        try:
            if self._recorder is not None:
                self._recorder.stop()
        except Exception as exc:
            self._finished = True
            self._write_context("abort_failed", extra={"abort_reason": reason, "failure": str(exc)})
            raise
        finally:
            if self._marker is not None:
                self._marker.close()
        self._finished = True
        self._write_context("aborted", extra={"abort_reason": reason})

    def recorder_summary(self) -> dict[str, dict[str, object]]:
        if self._recorder is None:
            return {}
        return self._recorder.summary()

    def _build_features(self, context: dict[str, object]) -> tuple[ReadinessFeatures, GateResult]:
        assert self._recorder is not None
        baseline_start, baseline_end = self._phase_bounds["baseline"]
        sart_start, sart_end = self._phase_bounds["sart"]
        baseline: dict[str, tuple[tuple[float, ...], tuple[tuple[float, ...], ...]]] = {}
        task: dict[str, tuple[tuple[float, ...], tuple[tuple[float, ...], ...]]] = {}
        for kind in ("eeg", "fnirs", "motion"):
            baseline[kind] = self._recorder.samples_between(kind, baseline_start, baseline_end)
            task[kind] = self._recorder.samples_between(kind, sart_start, sart_end)
        eeg_rate = self._sample_rate("eeg", (*baseline["eeg"][0], *task["eeg"][0]))
        eeg_baseline = _tail(baseline["eeg"][1], 2048)
        eeg_task = _tail(task["eeg"][1], 2048)
        payload = ScreeningInput(
            context=dict(context),
            sart_trials=tuple(self._trials),
            eeg_baseline=eeg_baseline,
            eeg_task=eeg_task,
            eeg_sample_rate=eeg_rate,
            fnirs_baseline=baseline["fnirs"][1],
            fnirs_task=task["fnirs"][1],
            motion_task=task["motion"][1],
            stream_timestamps={
                kind: (*baseline[kind][0], *task[kind][0])
                for kind in ("eeg", "fnirs", "motion")
            },
        )
        return process(payload)

    def _sample_rate(self, kind: str, timestamps: tuple[float, ...]) -> float:
        assert self._recorder is not None
        nominal = self._recorder.nominal_srate(kind)
        if nominal > 0:
            return nominal
        if len(timestamps) < 2:
            return 0.0
        duration = timestamps[-1] - timestamps[0]
        return (len(timestamps) - 1) / duration if duration > 0 else 0.0

    def _push(self, event: str, payload: dict[str, object], *, timestamp: float | None = None) -> None:
        if self._marker is None:
            raise RuntimeError("Marker Outlet 尚未启动")
        row = {
            "participant_id": self.participant_id,
            "sequence": self.sequence,
            **payload,
        }
        self._marker.push(event, row, self._clock() if timestamp is None else timestamp)

    def _require_recording(self) -> None:
        if not self._started or self._finished or self._recorder is None or self._marker is None:
            raise RuntimeError("当前没有进行中的 BrainCheck 采集")

    def _write_context(
        self,
        status: str,
        *,
        context: dict[str, object] | None = None,
        quality: dict[str, object] | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        payload = {
            "capture_schema_version": "1.0",
            "participant_id": self.participant_id,
            "sequence": self.sequence,
            "status": status,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "phase_bounds": self._phase_bounds,
            "trial_count": len(self._trials),
            "context": context or {},
            "quality": quality or {},
            "recorder_summary": self.recorder_summary(),
            **(extra or {}),
        }
        self.context_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _tail(
    samples: tuple[tuple[float, ...], ...],
    maximum: int,
) -> tuple[tuple[float, ...], ...]:
    if maximum <= 0:
        raise ValueError("maximum must be positive")
    return samples[-maximum:]
