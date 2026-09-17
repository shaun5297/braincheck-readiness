from __future__ import annotations

import argparse
import json
from pathlib import Path


def replay(
    xdf_path: Path,
    events_path: Path,
    context_path: Path,
    output: Path,
    *,
    model_manifest: Path | None = None,
    mode: str = "shadow",
    parent_assessment_id: str | None = None,
) -> dict:
    import numpy as np
    import pyxdf

    from ..acquisition.stream_schema import canonical_kind
    from ..inference.eegnet import attach_prediction
    from ..workflow.pipeline import ScreeningInput, process
    from ..workflow.screening import ScreeningService

    streams, _ = pyxdf.load_xdf(str(xdf_path))
    data = {
        canonical_kind(s["info"]["type"][0], s["info"]["name"][0]): s for s in streams
    }
    events = [json.loads(v) for v in events_path.read_text().splitlines() if v.strip()]
    times = {e["event"]: float(e["timestamp"]) for e in events}
    bounds = [
        (times["readiness_baseline_start"], times["readiness_baseline_end"]),
        (times["sart_start"], times["sart_end"]),
    ]
    selected = []
    for start, end in bounds:
        phase = {}
        for kind in ("eeg", "fnirs", "motion"):
            source = data[kind]
            ts = np.asarray(source["time_stamps"])
            values = np.asarray(source["time_series"])
            mask = (ts >= start) & (ts < end)
            phase[kind] = (ts[mask].tolist(), values[mask].tolist())
        selected.append(phase)
    baseline, task = selected
    context_doc = json.loads(context_path.read_text())
    values = context_doc.get("values", {})
    context = {
        "kss": values.get("kss_score"),
        "sleep_hours_24h": values.get("sleep_duration_hours"),
        "continuous_awake_hours": values.get("continuous_awake_hours"),
    }
    context = {k: v for k, v in context.items() if v is not None}
    trials = [
        e["payload"]
        for e in events
        if e["event"] == "sart_trial_result"
        and e["payload"].get("trial_kind") == "assessment"
        and not e["payload"].get("exclude_from_primary_analysis")
    ]
    rate = float(data["eeg"]["info"]["nominal_srate"][0])
    payload = ScreeningInput(
        context,
        trials,
        baseline["eeg"][1][-2048:],
        task["eeg"][1][-2048:],
        rate,
        baseline["fnirs"][1],
        task["fnirs"][1],
        task["motion"][1],
        {k: baseline[k][0] + task[k][0] for k in ("eeg", "fnirs", "motion")},
        motion_timestamps=task["motion"][0],
    )
    features, quality = process(payload)
    try:
        channels = tuple(
            c["label"][0]
            for c in data["eeg"]["info"]["desc"][0]["channels"][0]["channel"]
        )
    except (KeyError, IndexError, TypeError):
        channels = ("EEG-1", "EEG-2")
    attach_prediction(
        features,
        quality,
        model_manifest,
        [(a, b, *phase["eeg"]) for (a, b), phase in zip(bounds, selected, strict=True)],
        baseline["motion"][0] + task["motion"][0],
        baseline["motion"][1] + task["motion"][1],
        channel_names=channels,
        nominal_srate=rate,
    )
    features.metadata.update(
        {
            "acquisition_mode": "offline_xdf_replay",
            "source_xdf": str(xdf_path),
            "not_live_device_validation": True,
        }
    )
    service = ScreeningService(output, model_manifest, mode)
    identifier = "REPLAY"
    result = service.assess(
        identifier,
        features,
        quality,
        sequence=service.next_sequence(identifier),
        parent_assessment_id=parent_assessment_id,
    )
    return {
        "result": result.to_dict(),
        "quality": features.metadata.get("effective_quality", quality.to_dict()),
        "original_quality": quality.to_dict(),
        "eegnet": features.metadata.get("eegnet"),
        "source_xdf": str(xdf_path),
        "not_live_device_validation": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="只读回放 Dataset Studio XDF，结果写入单独目录"
    )
    parser.add_argument("--xdf", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path)
    parser.add_argument(
        "--mode", choices=("shadow", "assisted", "pilot_assisted"), default="shadow"
    )
    parser.add_argument("--parent-assessment-id")
    args = parser.parse_args()
    if args.mode == "assisted" and args.model_manifest is None:
        parser.error("assisted 需要 --model-manifest")
    report = replay(
        args.xdf,
        args.events,
        args.context,
        args.output,
        model_manifest=args.model_manifest,
        mode=args.mode,
        parent_assessment_id=args.parent_assessment_id,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
