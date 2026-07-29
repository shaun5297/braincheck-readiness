from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class BaselineProfile:
    participant_id: str
    baseline_session_count: int
    behavior: dict[str, float]
    eeg: dict[str, float]
    baseline_schema_version: str = "1.0"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load(path: Path) -> BaselineProfile | None:
    if not path.exists():
        return None
    row = json.loads(path.read_text(encoding="utf-8"))
    return BaselineProfile(
        participant_id=str(row["participant_id"]),
        baseline_session_count=int(row["baseline_session_count"]),
        behavior={key: float(value) for key, value in row.get("behavior", {}).items()},
        eeg={key: float(value) for key, value in row.get("eeg", {}).items()},
        baseline_schema_version=str(row.get("baseline_schema_version", "1.0")),
    )


def save(path: Path, profile: BaselineProfile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

