from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..workflow.screening import ScreeningService, demo_payload
from .self_test import run_self_test


def main() -> None:
    parser = argparse.ArgumentParser(description="脑安检班前认知准备度评估")
    parser.add_argument(
        "--data-root", type=Path, default=Path.home() / "Documents" / "BrainCheck"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="使用合成数据检查结果页面")
    mode.add_argument(
        "--competition-demo",
        action="store_true",
        help="执行真实采集流程；通过质量门控后显示明确标注的 normal 演示占位结果",
    )
    parser.add_argument(
        "--scenario", choices=("normal", "retest", "rest", "unable"), default="normal"
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--model-manifest", type=Path, help="BSense 导出的 EEGNet model_manifest.json"
    )
    parser.add_argument(
        "--eegnet-mode",
        choices=("shadow", "assisted", "pilot_assisted"),
        default=None,
        help="shadow 只记录预测；assisted 使用验证集阈值增加先导风险证据",
    )
    parser.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--no-eegnet", action="store_true", help="禁用本地已部署的先导 EEGNet"
    )
    args = parser.parse_args()
    if args.no_eegnet and args.model_manifest is not None:
        parser.error("--no-eegnet 与 --model-manifest 不能同时使用")
    deployed = (
        Path(__file__).resolve().parents[1]
        / "models"
        / "pilot_eegnet"
        / "model_manifest.json"
    )
    if (
        args.model_manifest is None
        and not args.no_eegnet
        and deployed.exists()
        and not (args.demo or args.competition_demo or args.self_test or args.headless)
    ):
        args.model_manifest = deployed
    if args.eegnet_mode is None:
        args.eegnet_mode = (
            "pilot_assisted" if args.model_manifest == deployed else "shadow"
        )
    if (
        args.eegnet_mode in {"assisted", "pilot_assisted"}
        and args.model_manifest is None
    ):
        parser.error("assisted 需要明确指定 --model-manifest")
    if args.model_manifest is not None:
        from ..inference.eegnet import EEGNetModel

        try:
            model = EEGNetModel(args.model_manifest)
            if args.eegnet_mode not in model.manifest.get(
                "allowed_modes", ["shadow", "assisted"]
            ):
                parser.error("所选模式不在该模型允许的部署配置中")
            if (
                args.eegnet_mode == "assisted"
                and float(model.manifest.get("calibration_balanced_accuracy", 0)) <= 0.5
            ):
                parser.error("该模型验证结果不支持辅助评分，可使用 shadow 记录")
        except (
            ImportError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
        ) as exc:
            parser.error(f"EEGNet 无法加载：{exc}")
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["ok"] else 1)
    if args.headless:
        features, quality = demo_payload(args.scenario)
        result = ScreeningService(args.data_root.resolve()).assess(
            "DEMO", features, quality
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return
    from ..app.main import run

    run(
        data_root=args.data_root.resolve(),
        demo=args.demo,
        competition_demo=args.competition_demo,
        scenario=args.scenario,
        debug=args.debug,
        model_manifest=args.model_manifest,
        eegnet_mode=args.eegnet_mode,
    )
