from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    PARTICIPANT = "participant"
    SUPERVISOR = "supervisor"
    DEBUG = "debug"


FIELDS_BY_ROLE = {
    Role.PARTICIPANT: {"assessment_id", "status", "label", "confidence", "data_quality", "reason_text", "recommended_action"},
    Role.SUPERVISOR: {"assessment_id", "participant_id", "status", "label", "data_quality", "recommended_action", "algorithm_version", "model_version"},
    Role.DEBUG: {"*"},
}


def project(payload: dict[str, object], role: Role) -> dict[str, object]:
    fields = FIELDS_BY_ROLE[role]
    return dict(payload) if "*" in fields else {key: payload[key] for key in fields if key in payload}

