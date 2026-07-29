from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping


def classify_sart_trial(should_respond: bool, response_time_s: float | None, *, valid: bool = True) -> dict[str, object]:
    responded = response_time_s is not None
    false_start = bool(responded and float(response_time_s) < 0.1)
    if false_start:
        outcome = "false_start" if should_respond else "commission"
    elif should_respond and responded:
        outcome = "hit"
    elif should_respond:
        outcome = "omission"
    elif responded:
        outcome = "commission"
    else:
        outcome = "correct_rejection"
    return {
        "should_respond": should_respond,
        "responded": responded,
        "reaction_time_s": response_time_s,
        "outcome": outcome,
        "false_start": false_start,
        "valid": valid,
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _slope(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean_x = (len(values) - 1) / 2
    mean_y = statistics.fmean(values)
    denominator = sum((index - mean_x) ** 2 for index in range(len(values)))
    return sum((index - mean_x) * (value - mean_y) for index, value in enumerate(values)) / denominator


def extract(trials: Iterable[Mapping[str, object]]) -> dict[str, float | int | None]:
    rows = [row for row in trials if row.get("valid", True)]
    go_count = sum(bool(row.get("should_respond")) for row in rows)
    no_go_count = len(rows) - go_count
    hit = sum(row.get("outcome") == "hit" for row in rows)
    omission = sum(row.get("outcome") == "omission" for row in rows)
    commission = sum(row.get("outcome") == "commission" for row in rows)
    correct_rejection = sum(row.get("outcome") == "correct_rejection" for row in rows)
    false_start = sum(bool(row.get("false_start")) for row in rows)
    reaction_times = [float(row["reaction_time_s"]) for row in rows if row.get("outcome") == "hit" and row.get("reaction_time_s") is not None]
    mean_rt = statistics.fmean(reaction_times) if reaction_times else None
    split = max(1, len(reaction_times) // 2)
    slow_count = max(1, math.ceil(len(reaction_times) * 0.1)) if reaction_times else 0
    return {
        "valid_trial_count": len(rows),
        "accuracy": _ratio(hit + correct_rejection, len(rows)),
        "omission_rate": _ratio(omission, go_count),
        "commission_rate": _ratio(commission, no_go_count),
        "false_start_rate": _ratio(false_start, len(rows)),
        "median_rt_s": round(statistics.median(reaction_times), 6) if reaction_times else None,
        "rt_cv": round(statistics.pstdev(reaction_times) / mean_rt, 6) if len(reaction_times) > 1 and mean_rt else None,
        "slowest_10_percent_rt_s": round(statistics.fmean(sorted(reaction_times)[-slow_count:]), 6) if reaction_times else None,
        "second_half_minus_first_half_rt_s": (
            round(statistics.fmean(reaction_times[split:]) - statistics.fmean(reaction_times[:split]), 6)
            if reaction_times[split:]
            else None
        ),
        "rt_slope": round(_slope(reaction_times), 8) if len(reaction_times) > 1 else None,
    }

