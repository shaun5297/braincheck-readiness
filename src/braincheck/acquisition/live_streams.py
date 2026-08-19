from __future__ import annotations

import threading
from collections import deque
from collections.abc import Sequence


class LiveBuffer:
    def __init__(self, channel_count: int, capacity: int = 200_000) -> None:
        self.channel_count = channel_count
        self._timestamps: deque[float] = deque(maxlen=capacity)
        self._samples: deque[tuple[float, ...]] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._arrival_inversion_count = 0

    def append(self, samples: Sequence[Sequence[float]], timestamps: Sequence[float]) -> int:
        rows = []
        for timestamp, sample in zip(timestamps, samples, strict=False):
            if len(sample) == self.channel_count:
                rows.append((float(timestamp), tuple(float(value) for value in sample)))
        with self._lock:
            for timestamp, row in rows:
                if self._timestamps and timestamp <= self._timestamps[-1]:
                    self._arrival_inversion_count += 1
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

    def between(
        self,
        start_timestamp: float,
        end_timestamp: float,
    ) -> tuple[tuple[float, ...], tuple[tuple[float, ...], ...]]:
        if end_timestamp < start_timestamp:
            raise ValueError("结束时间不能早于开始时间")
        with self._lock:
            rows = tuple(
                (timestamp, sample)
                for timestamp, sample in zip(self._timestamps, self._samples, strict=False)
                if start_timestamp <= timestamp <= end_timestamp
            )
        if not rows:
            return (), ()
        ordered = sorted(rows, key=lambda row: row[0])
        unique: list[tuple[float, tuple[float, ...]]] = []
        for row in ordered:
            if not unique or row[0] > unique[-1][0]:
                unique.append(row)
        return tuple(row[0] for row in unique), tuple(row[1] for row in unique)

    @property
    def arrival_inversion_count(self) -> int:
        with self._lock:
            return self._arrival_inversion_count
