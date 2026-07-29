from __future__ import annotations

from typing import Mapping


def compare_attempts(first: Mapping[str, object], retest: Mapping[str, object]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in ("kss", "omission_rate", "commission_rate", "median_rt_s", "rt_cv"):
        before, after = first.get(key), retest.get(key)
        result[f"{key}_change"] = round(float(after) - float(before), 6) if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None
    return result

