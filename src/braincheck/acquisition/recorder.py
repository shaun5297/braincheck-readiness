from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .discovery import discover
from .stream_schema import REQUIRED_KINDS
from .xdf_writer import XDFWriter


@dataclass
class _Stream:
    inlet: Any
    stream_id: int
    channels: int
    channel_format: int
    count: int = 0
    first: float = 0.0
    last: float = 0.0


class Recorder:
    def __init__(self, output: Path) -> None:
        self.output = output
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: Exception | None = None

    def start(self, timeout: float = 5.0) -> None:
        found = discover(timeout)
        missing = sorted(set(REQUIRED_KINDS) - found.keys())
        if missing:
            raise RuntimeError(f"缺少产品必需流：{', '.join(missing)}")
        from pylsl import StreamInlet

        writer = XDFWriter(self.output)
        streams = []
        for stream_id, kind in enumerate(REQUIRED_KINDS, 1):
            info, descriptor = found[kind]
            writer.header(stream_id, info.as_xml())
            streams.append(_Stream(StreamInlet(info, max_buflen=60), stream_id, descriptor.channel_count, int(info.channel_format())))

        def run() -> None:
            try:
                while not self._stop.is_set():
                    received = False
                    for state in streams:
                        samples, timestamps = state.inlet.pull_chunk(timeout=0.0, max_samples=1024)
                        if timestamps:
                            received = True
                            writer.samples(state.stream_id, timestamps, samples, state.channels, state.channel_format)
                            state.count += len(timestamps)
                            state.first = state.first or float(timestamps[0])
                            state.last = float(timestamps[-1])
                    if not received:
                        time.sleep(0.005)
            except Exception as exc:
                self.error = exc
            finally:
                for state in streams:
                    writer.footer(state.stream_id, state.first, state.last, state.count)
                writer.close()

        self._stop.clear()
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

