from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ReadinessFeatures:
    behavior: dict[str, float | int | None]
    eeg: dict[str, float | int | None]
    fnirs: dict[str, float | int | None]
    context: dict[str, object]
    quality: dict[str, object]
    feature_schema_version: str = "readiness_features_v1"
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

