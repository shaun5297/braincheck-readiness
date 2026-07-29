from __future__ import annotations

import math
from collections.abc import Sequence


def evaluate(samples: Sequence[Sequence[float]], *, rail_abs: float = 375_000.0) -> dict[str, object]:
    if not samples:
        return {"valid_channel_ratio": 0.0, "flat_channel_count": 0, "clipped_channel_count": 0}
    channel_count = min(len(row) for row in samples)
    valid = flat = clipped = 0
    for index in range(channel_count):
        values = [float(row[index]) for row in samples if math.isfinite(float(row[index]))]
        is_flat = bool(values) and max(values) - min(values) <= 1e-9
        is_clipped = any(abs(value) >= rail_abs for value in values)
        flat += is_flat
        clipped += is_clipped
        valid += bool(values) and not is_flat and not is_clipped
    return {
        "valid_channel_ratio": round(valid / channel_count, 6),
        "flat_channel_count": int(flat),
        "clipped_channel_count": int(clipped),
    }

