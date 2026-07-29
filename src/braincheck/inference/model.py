from __future__ import annotations

import json
import math
from pathlib import Path

from ..features.schema import ReadinessFeatures


class LogisticModel:
    def __init__(self, manifest_path: Path) -> None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.version = str(manifest["model_version"])
        self.features = tuple(manifest["features"])
        self.weights = tuple(float(value) for value in manifest["weights"])
        self.intercept = float(manifest["intercept"])
        if len(self.features) != len(self.weights):
            raise ValueError("model feature/weight mismatch")

    def predict(self, payload: ReadinessFeatures) -> float:
        sources = {**payload.behavior, **payload.eeg, **payload.fnirs, **payload.context}
        values = []
        for name in self.features:
            value = sources.get(name)
            if not isinstance(value, (int, float)):
                raise ValueError(f"模型输入缺少数值特征：{name}")
            values.append(float(value))
        logit = self.intercept + sum(weight * value for weight, value in zip(self.weights, values, strict=True))
        return 1 / (1 + math.exp(-max(-30, min(30, logit))))

