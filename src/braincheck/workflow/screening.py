from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from ..features import behavior as behavior_features
from ..features.schema import ReadinessFeatures
from ..inference.explanations import explain
from ..inference.fusion import infer
from ..inference.result import AssessmentResult
from ..quality.gate import GateResult
from .pipeline import ScreeningInput, process


def assessment_id(participant_id: str, sequence: int = 1, *, now: datetime | None = None) -> str:
    timestamp = now or datetime.now()
    return f"BC-{timestamp:%Y%m%d}-{participant_id}-{sequence:03d}"


@dataclass
class ScreeningService:
    data_root: Path
    model_manifest: Path | None = None

    def assess(
        self,
        participant_id: str,
        features: ReadinessFeatures,
        quality: GateResult,
        *,
        sequence: int = 1,
        parent_assessment_id: str | None = None,
    ) -> AssessmentResult:
        identifier = assessment_id(participant_id, sequence)
        if not quality.passed:
            codes = quality.reason_codes
            result = AssessmentResult(identifier, participant_id, "unable", 1.0, "failed", codes, explain(codes), "quality_gate_v1")
        else:
            status, confidence, codes, algorithm, model_version = infer(
                features,
                is_retest=parent_assessment_id is not None,
                model_manifest=self.model_manifest,
            )
            result = AssessmentResult(identifier, participant_id, status, confidence, "good", codes, explain(codes), algorithm, model_version)
        self._save(result, features, quality, parent_assessment_id)
        return result

    def _save(self, result: AssessmentResult, features: ReadinessFeatures, quality: GateResult, parent: str | None) -> None:
        directory = self.data_root / "assessments" / datetime.now().strftime("%Y-%m-%d") / result.assessment_id
        directory.mkdir(parents=True, exist_ok=False)
        files: dict[str, object] = {
            "result.json": result.to_dict(),
            "features.json": features.to_dict(),
            "quality.json": quality.to_dict(),
        }
        for filename, payload in files.items():
            (directory / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        audit = {
            "audit_schema_version": "1.0",
            "event": "assessment_completed",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "assessment_id": result.assessment_id,
            "parent_assessment_id": parent,
            "algorithm_version": result.algorithm_version,
            "model_version": result.model_version,
        }
        (directory / "audit.jsonl").write_text(json.dumps(audit, ensure_ascii=False) + "\n", encoding="utf-8")


def demo_payload(scenario: str) -> tuple[ReadinessFeatures, GateResult]:
    impaired = scenario in {"retest", "rest"}
    context: dict[str, object] = {
        "kss": 8 if impaired else 3,
        "sleep_hours_24h": 4.5 if impaired else 7.5,
        "continuous_awake_hours": 19 if impaired else 8,
        "shift": "夜班" if impaired else "日班",
    }
    trials = []
    for index in range(180):
        no_go = index % 9 == 0
        if no_go:
            response = 0.35 if impaired and index % 18 == 0 else None
        elif impaired and index % 7 == 0:
            response = None
        else:
            response = 0.35 + ((index % 5) * (0.10 if impaired else 0.01))
        trials.append(behavior_features.classify_sart_trial(not no_go, response))
    rate = 100.0
    eeg_baseline = [[math.sin(2 * math.pi * 10 * index / rate), math.sin(2 * math.pi * 10 * index / rate)] for index in range(200)]
    eeg_task = [
        [
            math.sin(2 * math.pi * (6 if impaired else 10) * index / rate),
            math.sin(2 * math.pi * (6 if impaired else 10) * index / rate),
        ]
        for index in range(200)
    ]
    if scenario == "unable":
        eeg_baseline = [[0.0, 0.0] for _ in range(200)]
        eeg_task = [[0.0, 0.0] for _ in range(200)]
    timestamps = [index / rate for index in range(200)]
    payload = ScreeningInput(
        context=context,
        sart_trials=trials,
        eeg_baseline=eeg_baseline,
        eeg_task=eeg_task,
        eeg_sample_rate=rate,
        fnirs_baseline=[[1.0 + index * 0.001 for _ in range(4)] for index in range(100)],
        fnirs_task=[[1.1 + index * 0.001 for _ in range(4)] for index in range(100)],
        motion_task=[[0.01 * math.sin(index / 10) for _ in range(6)] for index in range(100)],
        stream_timestamps={"eeg": timestamps, "fnirs": timestamps, "motion": timestamps},
    )
    features, quality = process(payload)
    features.metadata["demo_mode"] = True
    return features, quality
