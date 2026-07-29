from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .stream_schema import REQUIRED_KINDS, StreamDescriptor, canonical_kind


def _value(info: Any, method: str, default: object) -> object:
    try:
        return getattr(info, method)()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return default


def discover(timeout: float = 2.0, *, resolver: Callable[[float], Iterable[Any]] | None = None) -> dict[str, tuple[Any, StreamDescriptor]]:
    if resolver is None:
        from pylsl import resolve_streams

        resolver = resolve_streams
    grouped: dict[str, list[tuple[Any, StreamDescriptor]]] = {}
    for info in resolver(timeout):
        name = str(_value(info, "name", ""))
        kind = canonical_kind(str(_value(info, "type", "")), name)
        channels = int(_value(info, "channel_count", 0))
        if kind and channels > 0:
            descriptor = StreamDescriptor(kind, name, channels, float(_value(info, "nominal_srate", 0.0)))
            grouped.setdefault(kind, []).append((info, descriptor))
    duplicates = [kind for kind, values in grouped.items() if kind in REQUIRED_KINDS and len(values) > 1]
    if duplicates:
        raise RuntimeError(f"发现重复设备流：{', '.join(sorted(duplicates))}")
    return {kind: values[0] for kind, values in grouped.items()}

