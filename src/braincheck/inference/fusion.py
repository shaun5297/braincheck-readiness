from __future__ import annotations

from pathlib import Path
import json
import math

from ..features.schema import ReadinessFeatures
from .model import LogisticModel
from .rules import ALGORITHM_VERSION, infer as infer_rules


def infer(
    features: ReadinessFeatures,
    *,
    is_retest: bool,
    model_manifest: Path | None = None,
    eegnet_mode: str = "shadow",
) -> tuple[str, float, tuple[str, ...], str, str | None]:
    rule_status, rule_confidence, reasons = infer_rules(features, is_retest=is_retest)
    if model_manifest is None or not model_manifest.exists():
        return rule_status, rule_confidence, reasons, ALGORITHM_VERSION, None
    try:
        manifest = json.loads(model_manifest.read_text(encoding="utf-8"))
        if manifest.get("model_type") == "eegnet_torchscript":
            return _eegnet_fusion(
                features,
                manifest,
                rule_status,
                rule_confidence,
                reasons,
                is_retest=is_retest,
                mode=eegnet_mode,
            )
        model = LogisticModel(model_manifest)
        probability = model.predict(features)
    except (KeyError, OSError, TypeError, ValueError):
        return rule_status, rule_confidence, reasons, ALGORITHM_VERSION, None
    model_status = (
        "rest"
        if is_retest and probability >= 0.75
        else ("retest" if probability >= 0.55 else "normal")
    )
    severity = {"normal": 0, "retest": 1, "rest": 2}
    status = max((rule_status, model_status), key=severity.__getitem__)
    return (
        status,
        round(
            max(
                rule_confidence, probability if status != "normal" else 1 - probability
            ),
            2,
        ),
        reasons,
        f"{ALGORITHM_VERSION}+model_fusion_v1",
        model.version,
    )


def _eegnet_fusion(features, manifest, status, confidence, reasons, *, is_retest, mode):
    if mode not in {"shadow", "assisted", "pilot_assisted"}:
        raise ValueError("EEGNet mode 必须为 shadow 或 assisted")
    evidence = features.metadata.get("eegnet", {})
    if (
        not isinstance(evidence, dict)
        or evidence.get("status") != "ok"
        or manifest.get("available") is not True
        or manifest.get("training_source") != "bsense_reference_export"
        or evidence.get("model_sha256") != manifest.get("model_sha256")
    ):
        return status, confidence, reasons, ALGORITHM_VERSION, None
    version = str(manifest["model_version"])
    probability = float(evidence["p_impaired"])
    if manifest.get("training_mode") == "pilot_fit_only":
        if math.isfinite(probability) and 0 <= probability <= 1:
            if mode == "pilot_assisted" and mode in manifest.get("allowed_modes", []):
                policy = manifest.get("pilot_decision_policy", {})
                threshold = float(policy.get("threshold", -1))
                if not (
                    math.isfinite(threshold)
                    and 0 < threshold < 1
                    and policy.get("calibrated") is False
                    and policy.get("basis") == "engineering_demo_parameter"
                ):
                    return status, confidence, reasons, ALGORITHM_VERSION, None
                evidence["decision_mode"] = "pilot_assisted"
                evidence["engineering_threshold"] = threshold
                evidence["threshold_calibrated"] = False
                if probability >= threshold:
                    severity = {"normal": 0, "retest": 1, "rest": 2}
                    status = max(
                        (status, "rest" if is_retest else "retest"),
                        key=severity.__getitem__,
                    )
                    reasons = (*reasons, "eegnet_pilot_evidence")
                return (
                    status,
                    confidence,
                    reasons,
                    f"{ALGORITHM_VERSION}+eegnet_pilot_assisted_unvalidated",
                    version,
                )
            return (
                status,
                confidence,
                reasons,
                f"{ALGORITHM_VERSION}+eegnet_pilot_shadow",
                version,
            )
        return status, confidence, reasons, ALGORITHM_VERSION, None
    threshold = float(manifest["decision_threshold"])
    if not (
        math.isfinite(probability)
        and 0 <= probability <= 1
        and math.isfinite(threshold)
        and 0 < threshold < 1
    ):
        return status, confidence, reasons, ALGORITHM_VERSION, None
    if mode == "shadow":
        return (
            status,
            confidence,
            reasons,
            f"{ALGORITHM_VERSION}+eegnet_shadow",
            version,
        )
    # Assisted mode must be explicitly selected. An EEG score never downgrades rule risk.
    calibrated = (
        manifest.get("calibration_split") == "validation"
        and float(manifest.get("calibration_balanced_accuracy", 0)) > 0.5
    )
    if not calibrated:
        return (
            status,
            confidence,
            reasons,
            f"{ALGORITHM_VERSION}+eegnet_shadow",
            version,
        )
    if probability >= threshold:
        model_status = "rest" if is_retest else "retest"
        severity = {"normal": 0, "retest": 1, "rest": 2}
        status = max((status, model_status), key=severity.__getitem__)
        reasons = (*reasons, "eegnet_impaired_evidence")
    return (
        status,
        confidence,
        reasons,
        f"{ALGORITHM_VERSION}+eegnet_assisted_pilot",
        version,
    )
