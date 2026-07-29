from __future__ import annotations

from ..features.schema import ReadinessFeatures

ALGORITHM_VERSION = "pilot_rules_v2"


def score(features: ReadinessFeatures) -> tuple[int, tuple[str, ...]]:
    points = 0
    reasons: list[str] = []
    context, behavior, eeg = features.context, features.behavior, features.eeg

    def add(condition: bool, value: int, code: str) -> None:
        nonlocal points
        if condition:
            points += value
            reasons.append(code)

    add(float(context.get("kss", 0)) >= 7, 2, "high_sleepiness")
    add(float(context.get("sleep_hours_24h", 24)) < 5, 2, "short_sleep")
    add(float(context.get("continuous_awake_hours", 0)) >= 18, 2, "extended_wakefulness")
    add(float(behavior.get("omission_rate") or 0) >= 0.10, 2, "elevated_omission_rate")
    add(float(behavior.get("commission_rate") or 0) >= 0.20, 1, "elevated_commission_rate")
    add(float(behavior.get("rt_cv") or 0) >= 0.30, 2, "increased_rt_variability")
    behavior_z = max((abs(float(value)) for key, value in behavior.items() if key.endswith("_z") and value is not None), default=0.0)
    eeg_z = max((abs(float(value)) for key, value in eeg.items() if key.endswith("_z") and value is not None), default=0.0)
    add(behavior_z >= 2.0, 2, "behavior_shift_from_personal_baseline")
    add(eeg_z >= 2.0, 1, "eeg_shift_from_personal_baseline")
    add(behavior_z >= 2.0 and eeg_z >= 2.0, 1, "multimodal_shift")
    return points, tuple(dict.fromkeys(reasons))


def infer(features: ReadinessFeatures, *, is_retest: bool) -> tuple[str, float, tuple[str, ...]]:
    points, reasons = score(features)
    if is_retest:
        status = "rest" if points >= 3 else ("retest" if points == 2 else "normal")
    else:
        status = "retest" if points >= 2 else "normal"
    confidence = min(0.95, 0.55 + abs(points - 2) * 0.08)
    return status, round(confidence, 2), reasons

