from __future__ import annotations

import cmath
import math
import statistics
from collections.abc import Sequence

BANDS = {"theta": (4.0, 8.0), "alpha": (8.0, 13.0), "beta": (13.0, 30.0)}


def _power_spectrum(values: Sequence[float], sample_rate: float) -> list[tuple[float, float]]:
    centered = [float(value) - statistics.fmean(values) for value in values]
    count = len(centered)
    if count < 8 or sample_rate <= 0:
        return []
    spectrum = []
    for index in range(1, count // 2 + 1):
        frequency = index * sample_rate / count
        if frequency > 45:
            break
        value = sum(sample * cmath.exp(-2j * math.pi * index * position / count) for position, sample in enumerate(centered))
        spectrum.append((frequency, (abs(value) ** 2) / count))
    return spectrum


def extract(samples: Sequence[Sequence[float]], sample_rate: float) -> dict[str, float | int | None]:
    if not samples:
        return {"valid_window_ratio": 0.0}
    channel_count = min(len(row) for row in samples)
    channel_features: list[dict[str, float]] = []
    for channel in range(channel_count):
        spectrum = _power_spectrum([float(row[channel]) for row in samples], sample_rate)
        total = sum(power for frequency, power in spectrum if 1 <= frequency <= 40)
        if total <= 0:
            continue
        channel_features.append({
            name: sum(power for frequency, power in spectrum if low <= frequency < high) / total
            for name, (low, high) in BANDS.items()
        })
    if not channel_features:
        return {"valid_window_ratio": 0.0}
    theta = statistics.fmean(row["theta"] for row in channel_features)
    alpha = statistics.fmean(row["alpha"] for row in channel_features)
    beta = statistics.fmean(row["beta"] for row in channel_features)
    probabilities = [value for row in channel_features for value in row.values() if value > 0]
    entropy = -sum(value * math.log(value) for value in probabilities) / max(1, len(channel_features))
    return {
        "theta_relative": round(theta, 6),
        "alpha_relative": round(alpha, 6),
        "beta_relative": round(beta, 6),
        "theta_alpha_ratio": round(theta / alpha, 6) if alpha else None,
        "theta_alpha_over_beta": round((theta + alpha) / beta, 6) if beta else None,
        "spectral_entropy": round(entropy, 6),
        "frontal_asymmetry": round(channel_features[0]["alpha"] - channel_features[1]["alpha"], 6) if len(channel_features) >= 2 else None,
        "valid_window_ratio": round(len(channel_features) / channel_count, 6),
    }


def baseline_change(baseline: dict[str, float | int | None], task: dict[str, float | int | None]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in ("theta_relative", "alpha_relative", "beta_relative", "spectral_entropy"):
        before, after = baseline.get(key), task.get(key)
        result[f"{key}_change"] = round(float(after) - float(before), 6) if before is not None and after is not None else None
    return result

