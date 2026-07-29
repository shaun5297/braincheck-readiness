from __future__ import annotations

from collections.abc import Sequence


def evaluate(samples: Sequence[Sequence[float]], *, gyro_span_threshold: float = 5.0) -> dict[str, object]:
    if not samples:
        return {"artifact_window_ratio": 1.0, "stable": False}
    channel_count = min(len(row) for row in samples)
    spans = [max(float(row[index]) for row in samples) - min(float(row[index]) for row in samples) for index in range(channel_count)]
    gyro = spans[3:6] if len(spans) >= 6 else spans
    unstable = any(value > gyro_span_threshold for value in gyro)
    return {"artifact_window_ratio": 1.0 if unstable else 0.0, "stable": not unstable}

