from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


class MarkerOutlet:
    def __init__(self, audit_path: Path, outlet: Any | None = None) -> None:
        self.audit_path = audit_path
        if outlet is None:
            from pylsl import StreamInfo, StreamOutlet, cf_string

            outlet = StreamOutlet(
                StreamInfo(
                    "BrainCheck Markers",
                    "Markers",
                    1,
                    0,
                    cf_string,
                    f"braincheck-readiness-{uuid.uuid4().hex[:8]}",
                )
            )
        self.outlet: Any | None = outlet

    def push(self, event: str, payload: dict[str, object], timestamp: float) -> None:
        if self.outlet is None:
            raise RuntimeError("BrainCheck Marker Outlet 已关闭")
        row = {"marker_schema_version": "1.0", "event": event, "timestamp": timestamp, "payload": payload}
        encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        self.outlet.push_sample([encoded], timestamp)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")

    def close(self) -> None:
        outlet, self.outlet = self.outlet, None
        del outlet
