from __future__ import annotations

from ..inference.result import AssessmentResult
from ..privacy.access import Role, project


def build(result: AssessmentResult, *, personal_baseline_available: bool) -> dict[str, object]:
    payload = project(result.to_dict(), Role.PARTICIPANT)
    payload["scope_notice"] = "本结果仅描述当次班次状态，不是医疗诊断，也不构成自动化岗位决定。"
    payload["baseline_notice"] = (
        "已使用个人清醒基线"
        if personal_baseline_available
        else "当前使用群体先导参考范围；尚未建立个人清醒基线"
    )
    return payload

