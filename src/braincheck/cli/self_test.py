from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..features.schema import ReadinessFeatures
from ..privacy.access import Role, project
from ..workflow.screening import ScreeningService, demo_payload
from ..workflow.state_machine import State, StateMachine


def run_self_test() -> dict[str, object]:
    machine = StateMachine()
    for state in (State.IDENTITY, State.PRIVACY, State.CONTEXT, State.DEVICE, State.QUALITY, State.BASELINE, State.SART, State.FEATURES, State.RESULT):
        machine.advance(state)
    features, quality = demo_payload("retest")
    with tempfile.TemporaryDirectory(prefix="braincheck-self-test-") as directory:
        result = ScreeningService(Path(directory)).assess("SELFTEST", features, quality)
        supervisor = project(result.to_dict(), Role.SUPERVISOR)
        checks = {
            "fixed_workflow": machine.state == State.RESULT,
            "four_state_engine": result.status == "retest",
            "quality_gate": demo_payload("unable")[1].passed is False,
            "supervisor_hides_raw_features": "behavior" not in supervisor and "eeg" not in supervisor,
            "employment_decision_flag_false": result.validated_for_employment_decisions is False,
            "feature_schema": features.feature_schema_version == "readiness_features_v1",
        }
    return {"ok": all(checks.values()), "checks": checks}


def main() -> None:
    result = run_self_test()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)

