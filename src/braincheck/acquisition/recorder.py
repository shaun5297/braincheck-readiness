from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .discovery import discover
from .live_streams import LiveBuffer
from .stream_schema import REQUIRED_KINDS
from .xdf_writer import XDFWriter

_ANALYSIS_KINDS = ("eeg", "fnirs", "motion")


@dataclass
class _Stream:
    kind: str
    inlet: Any
    stream_id: int
    channels: int
    channel_format: int
    nominal_srate: float
    buffer: LiveBuffer | None = None
    clock_offset: float = 0.0
    next_clock_offset_at: float = 0.0
    count: int = 0
    first: float | None = None
    last: float | None = None


class Recorder:
    def __init__(self, output: Path) -> None:
        self.output = output
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._streams: dict[str, _Stream] = {}
        self.error: Exception | None = None

    def start(self, timeout: float = 5.0) -> None:
        found = discover(timeout)
        missing = sorted(set(REQUIRED_KINDS) - found.keys())
        if missing:
            raise RuntimeError(f"缺少产品必需流：{', '.join(missing)}")
        from pylsl import StreamInlet, local_clock

        writer = XDFWriter(self.output)
        streams: list[_Stream] = []
        try:
            for stream_id, kind in enumerate(REQUIRED_KINDS, 1):
                info, descriptor = found[kind]
                writer.header(stream_id, info.as_xml())
                inlet = StreamInlet(info, max_buflen=60)
                inlet.open_stream(timeout=timeout)
                try:
                    clock_offset = float(inlet.time_correction(timeout=min(timeout, 1.0)))
                except Exception:
                    clock_offset = 0.0
                writer.clock_offset(stream_id, float(local_clock()), clock_offset)
                streams.append(
                    _Stream(
                        kind,
                        inlet,
                        stream_id,
                        descriptor.channel_count,
                        int(info.channel_format()),
                        descriptor.nominal_srate,
                        LiveBuffer(descriptor.channel_count) if kind in _ANALYSIS_KINDS else None,
                        clock_offset,
                        time.monotonic() + 5.0,
                    )
                )
        except Exception:
            for state in streams:
                try:
                    state.inlet.close_stream()
                except Exception:
                    pass
            writer.close()
            raise

        def run() -> None:
            try:
                while not self._stop.is_set():
                    received = False
                    for state in streams:
                        monotonic_now = time.monotonic()
                        if monotonic_now >= state.next_clock_offset_at:
                            try:
                                state.clock_offset = float(state.inlet.time_correction(timeout=0.0))
                                writer.clock_offset(state.stream_id, float(local_clock()), state.clock_offset)
                            except Exception:
                                pass
                            state.next_clock_offset_at = monotonic_now + 5.0
                        samples, timestamps = state.inlet.pull_chunk(timeout=0.0, max_samples=1024)
                        if timestamps:
                            received = True
                            writer.samples(state.stream_id, timestamps, samples, state.channels, state.channel_format)
                            if state.buffer is not None:
                                corrected = [float(timestamp) + state.clock_offset for timestamp in timestamps]
                                state.buffer.append(samples, corrected)
                            state.count += len(timestamps)
                            if state.first is None:
                                state.first = float(timestamps[0])
                            state.last = float(timestamps[-1])
                    if not received:
                        time.sleep(0.005)
            except Exception as exc:
                self.error = exc
            finally:
                for state in streams:
                    writer.footer(
                        state.stream_id,
                        state.first if state.first is not None else 0.0,
                        state.last if state.last is not None else 0.0,
                        state.count,
                    )
                    try:
                        state.inlet.close_stream()
                    except Exception:
                        pass
                writer.close()

        self._stop.clear()
        self._streams = {state.kind: state for state in streams}
        self._thread = threading.Thread(target=run, name="braincheck-recorder", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)
        if self._thread and self._thread.is_alive():
            raise TimeoutError("recorder did not stop")
        if self.error:
            raise RuntimeError("recorder failed") from self.error

    def samples_between(
        self,
        kind: str,
        start_timestamp: float,
        end_timestamp: float,
    ) -> tuple[tuple[float, ...], tuple[tuple[float, ...], ...]]:
        state = self._streams.get(kind)
        if state is None or state.buffer is None:
            return (), ()
        return state.buffer.between(start_timestamp, end_timestamp)

    def nominal_srate(self, kind: str) -> float:
        state = self._streams.get(kind)
        return float(state.nominal_srate) if state is not None else 0.0

    def summary(self) -> dict[str, dict[str, object]]:
        return {
            kind: {
                "sample_count": state.count,
                "first_timestamp": state.first,
                "last_timestamp": state.last,
                "nominal_srate": state.nominal_srate,
                "clock_offset": state.clock_offset,
                "arrival_inversion_count": (
                    state.buffer.arrival_inversion_count if state.buffer is not None else 0
                ),
            }
            for kind, state in self._streams.items()
        }
