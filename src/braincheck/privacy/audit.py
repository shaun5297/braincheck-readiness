from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def append(path: Path, event: str, actor_role: str, details: dict[str, object] | None = None) -> None:
    row = {
        "audit_schema_version": "1.0",
        "event": event,
        "actor_role": actor_role,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")

