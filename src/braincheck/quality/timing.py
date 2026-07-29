from __future__ import annotations

from collections.abc import Mapping, Sequence


def evaluate(stream_timestamps: Mapping[str, Sequence[float]], required: Sequence[str]) -> dict[str, object]:
    missing = sorted(kind for kind in required if not stream_timestamps.get(kind))
    inversions = {
        kind: sum(current <= previous for previous, current in zip(values, values[1:]))
        for kind, values in stream_timestamps.items()
    }
    return {
        "stream_complete": not missing,
        "missing_streams": missing,
        "timestamp_inversion_count": sum(inversions.values()),
        "inversions_by_stream": inversions,
    }

