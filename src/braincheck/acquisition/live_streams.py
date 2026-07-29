from __future__ import annotations

import threading
from collections import deque
from collections.abc import Sequence


class LiveBuffer:
    def __init__(self, channel_count: int, capacity: int = 30_000) -> None:
        self.channel_count = channel_count
        self._timestamps: deque[float] = deque(maxlen=capacity)
        self._samples: deque[tuple[float, ...]] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def append(self, samples: Sequence[Sequence[float]], timestamps: Sequence[float]) -> int:
        rows = []
        for timestamp, sample in zip(timestamps, samples, strict=False):
            if len(sample) == self.channel_count:
                rows.append((float(timestamp), tuple(float(value) for value in sample)))
        with self._lock:
            for timestamp, row in rows:
                self._timestamps.append(timestamp)
                self._samples.append(row)
        return len(rows)

    def window(self, seconds: float) -> tuple[tuple[float, ...], tuple[tuple[float, ...], ...]]:
        with self._lock:
            timestamps, samples = tuple(self._timestamps), tuple(self._samples)
        if not timestamps:
            return (), ()
        cutoff = timestamps[-1] - seconds
        start = next((index for index, value in enumerate(timestamps) if value >= cutoff), len(timestamps))
        return timestamps[start:], samples[start:]

