from __future__ import annotations

import math
from collections.abc import Sequence


def evaluate(samples: Sequence[Sequence[float]], *, saturation_abs: float = 1e12) -> dict[str, object]:
    if not samples:
        return {"valid_channel_ratio": 0.0, "flat_channel_count": 0, "saturation_ratio": 1.0}
    channel_count = min(len(row) for row in samples)
    channels = [[float(row[index]) for row in samples if math.isfinite(float(row[index]))] for index in range(channel_count)]
    flat = sum(bool(values) and max(values) - min(values) <= 1e-9 for values in channels)
    saturated = sum(abs(value) >= saturation_abs for values in channels for value in values)
    total = sum(len(values) for values in channels)
    valid = sum(bool(values) and max(values) - min(values) > 1e-9 for values in channels)
    return {
        "valid_channel_ratio": round(valid / channel_count, 6),
        "flat_channel_count": flat,
        "saturation_ratio": round(saturated / total, 6) if total else 1.0,
    }

