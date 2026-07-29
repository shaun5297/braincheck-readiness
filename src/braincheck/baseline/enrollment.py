from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence

from .profile import BaselineProfile


def _aggregate(records: Sequence[Mapping[str, object]], keys: Sequence[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key in keys:
        values = [float(record[key]) for record in records if isinstance(record.get(key), (int, float))]
        if values:
            result[f"{key}_mean"] = round(statistics.fmean(values), 6)
            result[f"{key}_sd"] = round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0
    return result


def enroll(
    participant_id: str,
    behavior_sessions: Sequence[Mapping[str, object]],
    eeg_sessions: Sequence[Mapping[str, object]],
) -> BaselineProfile:
    if len(behavior_sessions) < 2 or len(eeg_sessions) < 2:
        raise ValueError("个人清醒基线至少需要两个不同日期的有效 Session")
    return BaselineProfile(
        participant_id=participant_id,
        baseline_session_count=min(len(behavior_sessions), len(eeg_sessions)),
        behavior=_aggregate(behavior_sessions, ("median_rt_s", "rt_cv", "omission_rate")),
        eeg=_aggregate(eeg_sessions, ("theta_relative", "alpha_relative", "spectral_entropy")),
    )

