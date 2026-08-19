from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .stream_schema import REQUIRED_KINDS, StreamDescriptor, canonical_kind


def _value(info: Any, method: str, default: object) -> object:
    try:
        return getattr(info, method)()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return default


def _identity(info: Any, descriptor: StreamDescriptor) -> tuple[object, ...] | None:
    uid = str(_value(info, "uid", "")).strip()
    source_id = descriptor.source_id.strip()
    if not uid and not source_id:
        return None
    return (
        ("uid", uid) if uid else ("source_id", source_id),
        descriptor.kind,
        descriptor.name,
        descriptor.stream_type,
        descriptor.channel_count,
        str(_value(info, "hostname", "")),
    )


def discover(timeout: float = 2.0, *, resolver: Callable[[float], Iterable[Any]] | None = None) -> dict[str, tuple[Any, StreamDescriptor]]:
    if resolver is None:
        from pylsl import resolve_streams

        resolver = resolve_streams
    grouped: dict[str, list[tuple[Any, StreamDescriptor]]] = {}
    seen: set[tuple[object, ...]] = set()
    for info in resolver(timeout):
        name = str(_value(info, "name", ""))
        stream_type = str(_value(info, "type", ""))
        kind = canonical_kind(stream_type, name)
        channels = int(_value(info, "channel_count", 0))
        if kind and channels > 0:
            descriptor = StreamDescriptor(
                kind,
                name,
                channels,
                float(_value(info, "nominal_srate", 0.0)),
                stream_type,
                str(_value(info, "source_id", "")),
            )
            identity = _identity(info, descriptor)
            if identity is not None and identity in seen:
                continue
            if identity is not None:
                seen.add(identity)
            grouped.setdefault(kind, []).append((info, descriptor))
    duplicates = [kind for kind, values in grouped.items() if kind in REQUIRED_KINDS and len(values) > 1]
    if duplicates:
        raise RuntimeError(f"发现重复设备流：{', '.join(sorted(duplicates))}")
    return {kind: values[0] for kind, values in grouped.items()}
