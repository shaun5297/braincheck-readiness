from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class State(StrEnum):
    WELCOME = "welcome"
    IDENTITY = "identity"
    PRIVACY = "privacy"
    CONTEXT = "context"
    DEVICE = "device"
    QUALITY = "quality"
    BASELINE = "baseline"
    SART = "sart"
    FEATURES = "features"
    RESULT = "result"
    RETEST_WAIT = "retest_wait"
    COMPLETE = "complete"
    STOPPED = "stopped"


_ORDER = (
    State.WELCOME,
    State.IDENTITY,
    State.PRIVACY,
    State.CONTEXT,
    State.DEVICE,
    State.QUALITY,
    State.BASELINE,
    State.SART,
    State.FEATURES,
    State.RESULT,
)


@dataclass
class StateMachine:
    state: State = State.WELCOME

    def advance(self, target: State) -> None:
        if target == State.STOPPED:
            self.state = target
            return
        if self.state == State.RESULT and target in {State.RETEST_WAIT, State.COMPLETE}:
            self.state = target
            return
        try:
            expected = _ORDER[_ORDER.index(self.state) + 1]
        except (ValueError, IndexError):
            raise ValueError(f"状态 {self.state} 不能推进到 {target}") from None
        if target != expected:
            raise ValueError(f"固定流程要求下一状态为 {expected}，不能跳到 {target}")
        self.state = target

