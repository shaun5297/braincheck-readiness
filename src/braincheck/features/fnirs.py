from __future__ import annotations

import statistics
from collections.abc import Sequence


def extract(
    baseline_samples: Sequence[Sequence[float]],
    task_samples: Sequence[Sequence[float]],
    *,
    artifact_window_ratio: float = 0.0,
) -> dict[str, float | int | None]:
    if not baseline_samples or not task_samples:
        return {"valid_window_ratio": 0.0, "motion_artifact_ratio": artifact_window_ratio}
    channel_count = min(min(len(row) for row in baseline_samples), min(len(row) for row in task_samples))
    changes = []
    drifts = []
    for index in range(channel_count):
        baseline = [float(row[index]) for row in baseline_samples]
        task = [float(row[index]) for row in task_samples]
        changes.append(statistics.fmean(task) - statistics.fmean(baseline))
        drifts.append(task[-1] - task[0])
    half = max(1, channel_count // 2)
    return {
        "optical_response_change": round(statistics.fmean(changes), 6),
        "baseline_drift": round(statistics.fmean(drifts), 6),
        "left_right_trend_difference": round(statistics.fmean(changes[:half]) - statistics.fmean(changes[half:]), 6) if changes[half:] else None,
        "motion_artifact_ratio": round(artifact_window_ratio, 6),
        "valid_window_ratio": 1.0,
    }

