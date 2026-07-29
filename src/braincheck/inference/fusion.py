from __future__ import annotations

from pathlib import Path

from ..features.schema import ReadinessFeatures
from .model import LogisticModel
from .rules import ALGORITHM_VERSION, infer as infer_rules


def infer(
    features: ReadinessFeatures,
    *,
    is_retest: bool,
    model_manifest: Path | None = None,
) -> tuple[str, float, tuple[str, ...], str, str | None]:
    rule_status, rule_confidence, reasons = infer_rules(features, is_retest=is_retest)
    if model_manifest is None or not model_manifest.exists():
        return rule_status, rule_confidence, reasons, ALGORITHM_VERSION, None
    try:
        model = LogisticModel(model_manifest)
        probability = model.predict(features)
    except (KeyError, OSError, TypeError, ValueError):
        return rule_status, rule_confidence, reasons, ALGORITHM_VERSION, None
    model_status = "rest" if is_retest and probability >= 0.75 else ("retest" if probability >= 0.55 else "normal")
    severity = {"normal": 0, "retest": 1, "rest": 2}
    status = max((rule_status, model_status), key=severity.__getitem__)
    return status, round(max(rule_confidence, probability if status != "normal" else 1 - probability), 2), reasons, f"{ALGORITHM_VERSION}+model_fusion_v1", model.version

