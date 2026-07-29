from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..app.main import run
from ..workflow.screening import ScreeningService, demo_payload
from .self_test import run_self_test


def main() -> None:
    parser = argparse.ArgumentParser(description="脑安检班前认知准备度评估")
    parser.add_argument("--data-root", type=Path, default=Path.home() / "Documents" / "BrainCheck")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--scenario", choices=("normal", "retest", "rest", "unable"), default="normal")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["ok"] else 1)
    if args.headless:
        features, quality = demo_payload(args.scenario)
        result = ScreeningService(args.data_root.resolve()).assess("DEMO", features, quality)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return
    run(data_root=args.data_root.resolve(), demo=args.demo, scenario=args.scenario, debug=args.debug)

