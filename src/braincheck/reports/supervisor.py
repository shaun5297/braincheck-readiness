from __future__ import annotations

from ..inference.result import AssessmentResult
from ..privacy.access import Role, project


def build(result: AssessmentResult, *, shift: str, retest_completed: bool) -> dict[str, object]:
    payload = project(result.to_dict(), Role.SUPERVISOR)
    payload.update({"shift": shift, "retest_required": result.status == "retest", "retest_completed": retest_completed})
    return payload

