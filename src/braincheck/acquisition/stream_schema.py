from __future__ import annotations

import re
from dataclasses import dataclass

REQUIRED_KINDS = ("eeg", "fnirs", "motion", "biomultilite_marker", "braincheck_marker")


def canonical_kind(stream_type: str, stream_name: str = "") -> str | None:
    values = {re.sub(r"[^a-z0-9]", "", value.lower()) for value in (stream_type, stream_name)}
    aliases = (
        ("braincheck_marker", {"braincheckmarkers"}),
        ("biomultilite_marker", {"biomultilitemarker", "biomultilitemarkers"}),
        ("fnirs", {"fnirs", "nirs", "nir", "ir"}),
        ("motion", {"motion", "imu"}),
        ("eeg", {"eeg"}),
    )
    for kind, candidates in aliases:
        if values.intersection(candidates):
            return kind
    if values.intersection({"marker", "markers"}):
        return "biomultilite_marker"
    return None


@dataclass(frozen=True)
class StreamDescriptor:
    kind: str
    name: str
    channel_count: int
    nominal_srate: float

