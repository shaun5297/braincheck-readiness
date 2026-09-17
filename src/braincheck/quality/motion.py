from __future__ import annotations

from collections.abc import Sequence
import bisect
import math


def evaluate(
    samples: Sequence[Sequence[float]],
    *,
    gyro_span_threshold: float = 5.0,
    timestamps: Sequence[float] = (),
) -> dict[str, object]:
    if not samples:
        return {"artifact_window_ratio": 1.0, "stable": False}
    if timestamps:
        if (
            len(timestamps) != len(samples)
            or not all(math.isfinite(t) for t in timestamps)
            or any(b <= a for a, b in zip(timestamps, timestamps[1:]))
        ):
            return {
                "artifact_window_ratio": 1.0,
                "stable": False,
                "invalid_timestamps": True,
            }
        flags = []
        cursor = timestamps[0]
        while cursor + 4 <= timestamps[-1]:
            start = bisect.bisect_left(timestamps, cursor)
            end = bisect.bisect_left(timestamps, cursor + 4)
            flags.append(
                float(
                    evaluate(
                        samples[start:end], gyro_span_threshold=gyro_span_threshold
                    )["artifact_window_ratio"]
                )
            )
            cursor += 2
        if flags:
            return {
                "artifact_window_ratio": sum(flags) / len(flags),
                "stable": not any(flags),
                "candidate_windows": len(flags),
                "window_seconds": 4.0,
                "step_seconds": 2.0,
            }
    channel_count = min(len(row) for row in samples)
    if channel_count < 6 or any(
        not math.isfinite(float(v)) for row in samples for v in row
    ):
        return {"artifact_window_ratio": 1.0, "stable": False}
    spans = [
        max(float(row[index]) for row in samples)
        - min(float(row[index]) for row in samples)
        for index in range(channel_count)
    ]
    gyro = spans[3:6] if len(spans) >= 6 else spans
    unstable = any(value > gyro_span_threshold for value in gyro)
    return {"artifact_window_ratio": 1.0 if unstable else 0.0, "stable": not unstable}
