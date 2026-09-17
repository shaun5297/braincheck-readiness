from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Sequence


class EEGNetModel:
    """Load an explicitly selected local BSense export, never a placeholder model."""

    def __init__(
        self, manifest_path: Path, *, allow_test_artifact: bool = False
    ) -> None:
        self.manifest_path = manifest_path.resolve()
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        m = self.manifest
        if m.get("training_source") != "bsense_reference_export" and not (
            allow_test_artifact and m.get("training_source") == "synthetic_test_fixture"
        ):
            raise ValueError("该模型不是自采 reference 模型，禁止用于现场判断")
        if (
            m.get("schema_version") != "braincheck-eegnet-v1"
            or m.get("available") is not True
            or m.get("model_type") != "eegnet_torchscript"
            or m.get("task") != "readiness_reference"
            or m.get("classes") != ["alert", "impaired"]
            or m.get("input_shape") != [2, 1000]
            or m.get("sample_rate_hz") != 250
            or m.get("window_seconds") != 4
            or m.get("step_seconds") != 2
            or m.get("preprocessing") != "embedded_demean_fft_1_40_train_channel_scale"
            or m.get("aggregation") != "mean_window_probability"
        ):
            raise ValueError("EEGNet 模型协议、标签或输入规格不匹配")
        pilot = m.get("training_mode") == "pilot_fit_only"
        threshold = (
            m.get("decision_threshold") if pilot else float(m["decision_threshold"])
        )
        if pilot:
            if (
                threshold is not None
                or m.get("calibration_split") != "none"
                or "shadow" not in m.get("allowed_modes", [])
                or not set(m.get("allowed_modes", [])) <= {"shadow", "pilot_assisted"}
                or m.get("independent_evaluation_available") is not False
            ):
                raise ValueError("未独立验证的先导模型只能旁路记录，不能带校准阈值")
            if "pilot_assisted" in m.get("allowed_modes", []):
                policy = m.get("pilot_decision_policy", {})
                cutoff = float(policy.get("threshold", -1))
                if (
                    not math.isfinite(cutoff)
                    or not 0 < cutoff < 1
                    or policy.get("calibrated") is not False
                    or policy.get("basis") != "engineering_demo_parameter"
                ):
                    raise ValueError("先导辅助模式需要明确标记的未校准工程阈值")
        elif (
            not math.isfinite(threshold)
            or not 0 < threshold < 1
            or m.get("calibration_split") != "validation"
        ):
            raise ValueError("模型缺少有效验证集阈值")
        if len(m.get("channel_names", [])) != 2:
            raise ValueError("模型缺少两通道顺序")
        splits = m.get("subject_splits", {})
        groups = [set(splits.get(k, [])) for k in ("train", "validation", "test")]
        if (
            not groups[0]
            or (not pilot and not all(groups))
            or (pilot and any(groups[1:]))
        ) or any(groups[i] & groups[j] for i in range(3) for j in range(i)):
            raise ValueError("模型被试划分缺失或存在交叉")
        model_path = (self.manifest_path.parent / m["model_file"]).resolve()
        if model_path.parent != self.manifest_path.parent:
            raise ValueError("模型文件必须位于导出目录内")
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != m["model_sha256"]:
            raise ValueError("模型 SHA256 不匹配")
        import torch

        self.model = torch.jit.load(str(model_path), map_location="cpu").eval()
        self.version = str(m["model_version"])

    def predict_windows(self, windows):
        import numpy as np
        import torch

        x = np.asarray(windows, dtype=np.float32)
        if (
            x.ndim != 3
            or x.shape[1:] != (2, 1000)
            or not len(x)
            or not np.isfinite(x).all()
        ):
            raise ValueError("模型需要有限 EEG[N,2,1000]")
        with torch.inference_mode():
            output = self.model(torch.from_numpy(x)).numpy()
        if (
            output.shape != (len(x), 2)
            or not np.isfinite(output).all()
            or np.any(output < 0)
            or np.any(output > 1)
            or not np.allclose(output.sum(axis=1), 1, atol=1e-5)
        ):
            raise ValueError("模型输出不是有效的二分类概率")
        return output

    def predict_segments(
        self,
        segments: Sequence[tuple],
        motion_timestamps: Sequence[float],
        motion_samples: Sequence[Sequence[float]],
        *,
        channel_names: Sequence[str],
        nominal_srate: float,
    ) -> dict[str, object]:
        import numpy as np

        if list(channel_names) != self.manifest["channel_names"]:
            raise ValueError("现场 EEG 通道顺序与训练不一致")
        if not math.isfinite(nominal_srate) or not math.isclose(
            nominal_srate, 250, rel_tol=0.02
        ):
            raise ValueError("现场 EEG 采样率与训练域不一致")
        mt = np.asarray(motion_timestamps, dtype=float)
        motion = np.asarray(motion_samples, dtype=float)
        if (
            len(mt) < 2
            or motion.ndim != 2
            or motion.shape != (len(mt), 6)
            or not np.isfinite(mt).all()
            or not np.isfinite(motion).all()
            or np.any(np.diff(mt) <= 0)
        ):
            raise ValueError("运动数据或时间戳无效")
        windows = []
        total = 0
        for start, end, timestamps, samples in segments:
            ts = np.asarray(timestamps, dtype=float)
            values = np.asarray(samples, dtype=float)
            if (
                not math.isfinite(start)
                or not math.isfinite(end)
                or end <= start
                or len(ts) < 2
                or values.shape != (len(ts), 2)
                or not np.isfinite(ts).all()
                or not np.isfinite(values).all()
                or np.any(np.diff(ts) <= 0)
            ):
                raise ValueError("EEG 区间、数据或时间戳无效")
            for cursor in np.arange(start, end - 4 + 1e-6, 2):
                total += 1
                a, b = np.searchsorted(ts, [cursor, cursor + 4])
                c, d = np.searchsorted(mt, [cursor, cursor + 4])
                eeg = values[a:b]
                gyro = motion[c:d, 3:6]
                if len(eeg) < 800 or len(gyro) < 2:
                    continue
                valid = (np.ptp(eeg, axis=0) > 1e-9) & (
                    np.max(np.abs(eeg), axis=0) < 375000
                )
                if valid.mean() < 0.5 or np.any(np.ptp(gyro, axis=0) > 5):
                    continue
                # Reject gaps/edge extrapolation rather than manufacture coverage.
                if (
                    ts[a] > cursor + 0.1
                    or ts[b - 1] < cursor + 3.896
                    or np.max(np.diff(ts[a:b])) > 0.1
                ):
                    continue
                if mt[c] > cursor + 0.5 or mt[d - 1] < cursor + 3.5:
                    continue
                target = cursor + np.arange(1000) / 250
                windows.append(
                    np.vstack(
                        [np.interp(target, ts[a:b], eeg[:, ch]) for ch in range(2)]
                    )
                )
        if not windows:
            raise ValueError("没有通过 EEG/Motion 窗口门控的模型输入")
        values = self.predict_windows(np.stack(windows))[:, 1]
        return {
            "status": "ok",
            "model_version": self.version,
            "model_sha256": self.manifest["model_sha256"],
            "p_impaired": float(values.mean()),
            "window_count": len(values),
            "candidate_windows": total,
            "threshold": self.manifest["decision_threshold"],
            "calibration_split": self.manifest["calibration_split"],
            "training_mode": self.manifest.get("training_mode", "subject_independent"),
            "experimental": True,
            "field_validated": False,
        }


def attach_prediction(
    features,
    quality,
    manifest_path: Path | None,
    segments,
    motion_timestamps,
    motion_samples,
    *,
    channel_names,
    nominal_srate,
) -> None:
    if manifest_path is None:
        return
    if not quality.passed:
        # A pilot may log clean-window predictions while the four-state result
        # remains unable. Missing signals and other quality failures still block.
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            salvage = (
                m.get("training_mode") == "pilot_fit_only"
                and m.get("quality_profile") == "pilot_clean_windows"
                and set(quality.reason_codes) == {"excessive_motion"}
            )
        except (OSError, ValueError, TypeError):
            salvage = False
        if not salvage:
            features.metadata["eegnet"] = {"status": "skipped_quality_gate"}
            return
    try:
        model = EEGNetModel(manifest_path)
        features.metadata["eegnet"] = model.predict_segments(
            segments,
            motion_timestamps,
            motion_samples,
            channel_names=channel_names,
            nominal_srate=nominal_srate,
        )
        features.metadata["eegnet"]["overall_quality_passed"] = quality.passed
        features.metadata["eegnet"]["decision_override"] = False
    except (ImportError, OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        features.metadata["eegnet"] = {"status": "unavailable", "reason": str(exc)}
