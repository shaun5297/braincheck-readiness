from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason_codes: tuple[str, ...]
    metrics: dict[str, object]
    quality_schema_version: str = "1.0"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate(
    eeg: Mapping[str, object],
    fnirs: Mapping[str, object],
    motion: Mapping[str, object],
    timing: Mapping[str, object],
    *,
    valid_sart_trials: int,
    expected_sart_trials: int = 180,
) -> GateResult:
    reasons: list[str] = []
    if float(eeg.get("valid_channel_ratio", 0)) < 0.5:
        reasons.append("eeg_quality_insufficient")
    if float(fnirs.get("valid_channel_ratio", 0)) < 0.5:
        reasons.append("fnirs_quality_insufficient")
    if float(fnirs.get("saturation_ratio", 1)) > 0.1:
        reasons.append("fnirs_saturation")
    if float(motion.get("artifact_window_ratio", 1)) > 0.2:
        reasons.append("excessive_motion")
    if not timing.get("stream_complete"):
        reasons.append("lsl_stream_incomplete")
    if int(timing.get("timestamp_inversion_count", 1)) > 0:
        reasons.append("invalid_lsl_timestamps")
    if valid_sart_trials < max(1, round(expected_sart_trials * 0.9)):
        reasons.append("insufficient_valid_trials")
    return GateResult(not reasons, tuple(dict.fromkeys(reasons)), {
        "eeg": dict(eeg),
        "fnirs": dict(fnirs),
        "motion": dict(motion),
        "lsl": dict(timing),
        "valid_sart_trials": valid_sart_trials,
    })

