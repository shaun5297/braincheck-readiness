from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaselineTask:
    duration_seconds: int = 45
    instruction: str = "请注视中央，保持自然呼吸，尽量不要说话或移动"

