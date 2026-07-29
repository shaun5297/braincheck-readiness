from __future__ import annotations

from dataclasses import asdict, dataclass


STATUS_LABELS = {
    "normal": "正常",
    "retest": "建议复测",
    "rest": "建议休息",
    "unable": "无法评估",
}

ACTIONS = {
    "normal": "进入单位正常流程",
    "retest": "离屏休息10至15分钟后复测",
    "rest": "暂停高风险操作并进行人工评估",
    "unable": "调整设备并重新采集",
}


@dataclass(frozen=True)
class AssessmentResult:
    assessment_id: str
    participant_id: str
    status: str
    confidence: float
    data_quality: str
    reason_codes: tuple[str, ...]
    reason_text: tuple[str, ...]
    algorithm_version: str
    model_version: str | None = None
    result_schema_version: str = "1.0"
    validated_for_employment_decisions: bool = False

    @property
    def label(self) -> str:
        return STATUS_LABELS[self.status]

    @property
    def recommended_action(self) -> str:
        return ACTIONS[self.status]

    def to_dict(self) -> dict[str, object]:
        row = asdict(self)
        row["label"] = self.label
        row["recommended_action"] = self.recommended_action
        return row

