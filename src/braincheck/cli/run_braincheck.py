from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..workflow.screening import ScreeningService, demo_payload
from .self_test import run_self_test


def main() -> None:
    parser = argparse.ArgumentParser(description="脑安检班前认知准备度评估")
    parser.add_argument("--data-root", type=Path, default=Path.home() / "Documents" / "BrainCheck")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="使用合成数据检查结果页面")
    mode.add_argument(
        "--competition-demo",
        action="store_true",
        help="执行真实采集流程；通过质量门控后显示明确标注的 normal 演示占位结果",
    )
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
    from ..app.main import run

    run(
        data_root=args.data_root.resolve(),
        demo=args.demo,
        competition_demo=args.competition_demo,
        scenario=args.scenario,
        debug=args.debug,
    )
