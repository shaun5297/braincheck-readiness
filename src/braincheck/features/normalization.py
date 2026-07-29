from __future__ import annotations

from typing import Mapping


def z_score(value: float | None, mean: float | None, sd: float | None) -> float | None:
    if value is None or mean is None or sd is None or sd <= 0:
        return None
    return round((value - mean) / sd, 6)


def compare_to_personal(values: Mapping[str, object], baseline: Mapping[str, object]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key, value in values.items():
        mean = baseline.get(f"{key}_mean")
        sd = baseline.get(f"{key}_sd")
        if isinstance(value, (int, float)) and isinstance(mean, (int, float)) and isinstance(sd, (int, float)):
            result[f"{key}_z"] = z_score(float(value), float(mean), float(sd))
    return result

