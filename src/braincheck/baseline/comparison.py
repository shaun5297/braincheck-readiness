from __future__ import annotations

from ..features.normalization import compare_to_personal
from .profile import BaselineProfile


def compare(behavior: dict[str, object], eeg: dict[str, object], profile: BaselineProfile | None) -> tuple[dict[str, object], dict[str, object], bool]:
    if profile is None:
        return dict(behavior), dict(eeg), False
    behavior_result = {**behavior, **compare_to_personal(behavior, profile.behavior)}
    eeg_result = {**eeg, **compare_to_personal(eeg, profile.eeg)}
    return behavior_result, eeg_result, True

