from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path
from typing import Sequence


def _varint(value: int) -> bytes:
    if value < 256:
        return b"\x01" + struct.pack("<B", value)
    if value <= 0xFFFFFFFF:
        return b"\x04" + struct.pack("<I", value)
    return b"\x08" + struct.pack("<Q", value)


class XDFWriter:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = path.open("xb")
        self._stream.write(b"XDF:")
        self._chunk(1, f'<info><version>1.0</version><datetime>{datetime.now().astimezone().isoformat()}</datetime></info>'.encode())

    def _chunk(self, tag: int, content: bytes, stream_id: int | None = None) -> None:
        prefix = b"" if stream_id is None else struct.pack("<I", stream_id)
        self._stream.write(_varint(2 + len(prefix) + len(content)) + struct.pack("<H", tag) + prefix + content)
        self._stream.flush()

    def header(self, stream_id: int, xml: str) -> None:
        self._chunk(2, xml.encode(), stream_id)

    def samples(self, stream_id: int, timestamps: Sequence[float], samples: Sequence[Sequence[object]], channel_count: int, channel_format: int) -> None:
        if not timestamps:
            return
        formats = {1: "f", 2: "d", 4: "i", 5: "h", 6: "b", 7: "q"}
        formatter = struct.Struct("<" + formats[channel_format] * channel_count) if channel_format in formats else None
        payload = bytearray(b"\x04" + struct.pack("<I", len(timestamps)))
        for timestamp, sample in zip(timestamps, samples, strict=True):
            payload.extend(b"\x08" + struct.pack("<d", float(timestamp)))
            if channel_format == 3:
                for value in sample:
                    encoded = str(value).encode()
                    payload.extend(_varint(len(encoded)) + encoded)
            elif formatter:
                payload.extend(formatter.pack(*sample))
            else:
                raise ValueError(f"unsupported channel format: {channel_format}")
        self._chunk(3, bytes(payload), stream_id)

    def footer(self, stream_id: int, first: float, last: float, count: int) -> None:
        self._chunk(6, f"<info><first_timestamp>{first}</first_timestamp><last_timestamp>{last}</last_timestamp><sample_count>{count}</sample_count></info>".encode(), stream_id)

    def close(self) -> None:
        self._stream.close()

