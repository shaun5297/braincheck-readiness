from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..baseline.comparison import compare
from ..baseline.profile import BaselineProfile
from ..features import behavior as behavior_features
from ..features import eeg as eeg_features
from ..features import fnirs as fnirs_features
from ..features.schema import ReadinessFeatures
from ..quality import eeg as eeg_quality
from ..quality import fnirs as fnirs_quality
from ..quality import motion as motion_quality
from ..quality import timing as timing_quality
from ..quality.gate import GateResult, evaluate as quality_gate


@dataclass(frozen=True)
class ScreeningInput:
    context: Mapping[str, object]
    sart_trials: Sequence[Mapping[str, object]]
    eeg_baseline: Sequence[Sequence[float]]
    eeg_task: Sequence[Sequence[float]]
    eeg_sample_rate: float
    fnirs_baseline: Sequence[Sequence[float]]
    fnirs_task: Sequence[Sequence[float]]
    motion_task: Sequence[Sequence[float]]
    stream_timestamps: Mapping[str, Sequence[float]]


def process(
    payload: ScreeningInput,
    *,
    personal_baseline: BaselineProfile | None = None,
    expected_trials: int = 180,
) -> tuple[ReadinessFeatures, GateResult]:
    behavior = behavior_features.extract(payload.sart_trials)
    eeg_baseline_features = eeg_features.extract(payload.eeg_baseline, payload.eeg_sample_rate)
    eeg = eeg_features.extract(payload.eeg_task, payload.eeg_sample_rate)
    eeg.update(eeg_features.baseline_change(eeg_baseline_features, eeg))
    motion = motion_quality.evaluate(payload.motion_task)
    fnirs = fnirs_features.extract(
        payload.fnirs_baseline,
        payload.fnirs_task,
        artifact_window_ratio=float(motion["artifact_window_ratio"]),
    )
    behavior, eeg, has_personal = compare(behavior, eeg, personal_baseline)
    eeg_q = eeg_quality.evaluate([*payload.eeg_baseline, *payload.eeg_task])
    fnirs_q = fnirs_quality.evaluate([*payload.fnirs_baseline, *payload.fnirs_task])
    timing_q = timing_quality.evaluate(payload.stream_timestamps, ("eeg", "fnirs", "motion"))
    gate = quality_gate(
        eeg_q,
        fnirs_q,
        motion,
        timing_q,
        valid_sart_trials=int(behavior["valid_trial_count"] or 0),
        expected_sart_trials=expected_trials,
    )
    features = ReadinessFeatures(
        behavior=behavior,
        eeg=eeg,
        fnirs=fnirs,
        context=dict(payload.context),
        quality=gate.metrics,
        metadata={"personal_baseline_available": has_personal},
    )
    return features, gate

