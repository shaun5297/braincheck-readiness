from __future__ import annotations

import tkinter as tk
import time
from collections.abc import Callable
from pathlib import Path
from tkinter import StringVar, messagebox, ttk

from ..tasks.sart import stimulus_sequence
from ..workflow.live_screening import LiveScreeningOutcome, LiveScreeningSession
from ..workflow.timing import BASELINE_SECONDS, QUALITY_SECONDS, SART_SECONDS, SART_TRIAL_COUNT
from .theme import BG, FONT_FAMILY, PHASE_COLORS, PRIMARY, TEXT, TEXT_MUTED

PHASE_NAMES = {
    "connecting": "连接设备",
    "quality": "信号质量检查",
    "baseline": "睁眼基线",
    "sart": "SART 任务",
    "processing": "生成结果",
}


class OperatorView(ttk.Frame):
    def __init__(
        self,
        parent: object,
        *,
        on_live_complete: Callable[[LiveScreeningOutcome], None],
        on_demo_complete: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__(parent, padding=24)
        self._on_live_complete = on_live_complete
        self._on_demo_complete = on_demo_complete
        self._on_cancel = on_cancel
        self._session: LiveScreeningSession | None = None
        self._context: dict[str, object] = {}
        self._after_ids: set[str] = set()
        self._phase_deadline = 0.0
        self._phase_duration = 0.0
        self._phase_offset = 0.0
        self._phase_done: Callable[[], None] | None = None
        self._stimuli: tuple[str, ...] = ()
        self._trial_index = 0
        self._trial_stimulus_timestamp: float | None = None
        self._trial_response_timestamp: float | None = None

        self.status = StringVar(value="等待开始")
        self.detail = StringVar(value="")
        self.countdown = StringVar(value="")
        self.signal_status = StringVar(value="EEG / fNIRS / Motion：尚未连接")

        ttk.Label(self, text="设备与任务", style="Title.TLabel").pack(anchor="center", pady=(0, 4))
        self.phase_badge = tk.Label(
            self,
            text="",
            font=(FONT_FAMILY, 13, "bold"),
            padx=20,
            pady=6,
        )
        self.phase_badge.pack(pady=(8, 4))
        tk.Label(
            self,
            textvariable=self.status,
            font=(FONT_FAMILY, 34, "bold"),
            fg=PRIMARY,
            bg=BG,
        ).pack(fill="both", expand=True, pady=(20, 6))
        ttk.Label(
            self,
            textvariable=self.detail,
            font=(FONT_FAMILY, 15),
            wraplength=680,
            justify="center",
            anchor="center",
        ).pack(fill="x", pady=6)
        tk.Label(
            self,
            textvariable=self.countdown,
            font=(FONT_FAMILY, 18, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(fill="x", pady=6)
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=QUALITY_SECONDS + BASELINE_SECONDS + SART_SECONDS)
        self.progress.pack(fill="x", pady=14)
        ttk.Label(
            self,
            textvariable=self.signal_status,
            style="Muted.TLabel",
            wraplength=680,
        ).pack(fill="x", pady=6)
        actions = ttk.Frame(self)
        actions.pack(fill="x")
        self.cancel_button = ttk.Button(
            actions,
            text="中止采集",
            command=self._request_abort,
            state="disabled",
            takefocus=False,
        )
        self.cancel_button.pack(side="left")
        self.action_button = ttk.Button(
            actions,
            text="生成演示结果",
            command=self._on_demo_complete,
            state="disabled",
            takefocus=False,
        )
        self.action_button.pack(side="right")

    def begin(
        self,
        *,
        data_root: Path,
        participant_id: str,
        sequence: int,
        context: dict[str, object],
        synthetic_demo: bool,
    ) -> None:
        self._cancel_scheduled()
        # 把键盘焦点从"开始检测"等按钮上移开，避免 SART 任务中的空格键误触发按钮
        # （ttk 按钮在有焦点时，空格键会先被按钮 class 绑定处理并激活按钮）。
        self.focus_set()
        self._session = None
        self._stimuli = ()
        self._trial_stimulus_timestamp = None
        self._trial_response_timestamp = None
        self._context = dict(context)
        self.progress.configure(value=0)
        self._set_phase("connecting")
        if synthetic_demo:
            self.status.set("合成情景演示")
            self.detail.set("此入口不连接设备，仅用于检查四态结果页面。真实功能视频请使用比赛演示模式。")
            self.countdown.set("")
            self.signal_status.set("数据来源：合成演示数据")
            self.phase_badge.config(text="演示模式", bg="#EAF1FC", fg=PRIMARY)
            self.action_button.configure(state="normal")
            self.cancel_button.configure(state="normal", text="返回", command=self._on_cancel)
            return

        self.action_button.configure(state="disabled")
        self.cancel_button.configure(state="normal", text="中止采集", command=self._request_abort)
        self.status.set("正在连接设备…")
        self.detail.set("正在创建 BrainCheck Marker 并检查 EEG、fNIRS、Motion 与设备 Marker 流。")
        self.signal_status.set("正在扫描 LSL")
        self.update_idletasks()
        session = LiveScreeningSession(data_root, participant_id, sequence=sequence)
        try:
            session.start()
        except Exception as exc:
            self.status.set("无法开始采集")
            self.detail.set(str(exc))
            self.signal_status.set("请确认 BSense-R 数据流已启动且没有重复流")
            self.cancel_button.configure(text="返回", command=self._on_cancel)
            messagebox.showerror("无法开始采集", str(exc), parent=self)
            return
        self._session = session
        self.bind_all("<space>", self._handle_space)
        self._start_quality()

    def _start_quality(self) -> None:
        assert self._session is not None
        self._session.start_phase("quality")
        self._set_phase("quality")
        self.status.set("信号质量检查")
        self.detail.set("请保持睁眼、自然呼吸，尽量不要说话或移动。")
        self._start_timed_phase(QUALITY_SECONDS, 0, self._finish_quality)

    def _finish_quality(self) -> None:
        assert self._session is not None
        self._session.end_phase("quality")
        self._session.start_phase("baseline")
        self._set_phase("baseline")
        self.status.set("睁眼基线")
        self.detail.set("请注视中央，保持放松和清醒。")
        self._start_timed_phase(BASELINE_SECONDS, QUALITY_SECONDS, self._finish_baseline)

    def _finish_baseline(self) -> None:
        assert self._session is not None
        self._session.end_phase("baseline")
        self.status.set("SART 任务说明")
        self.detail.set("除数字 3 外均按空格；看到 3 时不要按。任务持续 3 分钟。")
        self.countdown.set("3 秒后开始")
        self._schedule(3000, self._start_sart)

    def _start_sart(self) -> None:
        assert self._session is not None
        self._session.start_phase("sart")
        self._set_phase("sart")
        self._stimuli = stimulus_sequence(count=SART_TRIAL_COUNT, seed=self._session.sequence)
        self._trial_index = 0
        self.detail.set("除数字 3 外均按空格；看到 3 时不要按")
        self._start_trial()

    def _start_trial(self) -> None:
        assert self._session is not None
        if self._trial_index >= len(self._stimuli):
            self._session.end_phase("sart")
            self._set_phase("processing")
            self.status.set("正在生成结果…")
            self.detail.set("正在完成特征提取和数据质量门控。")
            self.countdown.set("")
            self._schedule(50, self._finish_live_collection)
            return
        stimulus = self._stimuli[self._trial_index]
        self.status.set(stimulus)
        self._trial_stimulus_timestamp = self._session.start_trial(
            trial=self._trial_index + 1,
            stimulus=stimulus,
        )
        self._trial_response_timestamp = None
        remaining = len(self._stimuli) - self._trial_index
        self.countdown.set(f"正式任务 · {self._trial_index + 1}/{len(self._stimuli)} · 约剩余 {remaining} 秒")
        self.progress.configure(value=QUALITY_SECONDS + BASELINE_SECONDS + self._trial_index)
        self._update_signal_status()
        self._schedule(500, lambda: self.status.set("+"))
        self._schedule(1000, self._finish_trial)

    def _finish_trial(self) -> None:
        assert self._session is not None
        stimulus = self._stimuli[self._trial_index]
        response_time = None
        if self._trial_response_timestamp is not None and self._trial_stimulus_timestamp is not None:
            response_time = max(0.0, self._trial_response_timestamp - self._trial_stimulus_timestamp)
        self._session.record_trial(
            trial=self._trial_index + 1,
            stimulus=stimulus,
            response_time_s=response_time,
            stimulus_timestamp=self._trial_stimulus_timestamp,
            response_timestamp=self._trial_response_timestamp,
        )
        self._trial_index += 1
        self._start_trial()

    def _finish_live_collection(self) -> None:
        session = self._session
        if session is None:
            return
        try:
            outcome = session.finish(self._context)
        except Exception as exc:
            self._session = None
            self.unbind_all("<space>")
            self.status.set("采集结束，但结果生成失败")
            self.detail.set(str(exc))
            self.cancel_button.configure(text="返回", command=self._on_cancel)
            messagebox.showerror("结果生成失败", str(exc), parent=self)
            return
        self._session = None
        self.unbind_all("<space>")
        self.progress.configure(value=self.progress["maximum"])
        self._on_live_complete(outcome)

    def _set_phase(self, phase: str) -> None:
        colors = PHASE_COLORS.get(phase, PHASE_COLORS["processing"])
        self.phase_badge.config(
            text=PHASE_NAMES.get(phase, phase),
            bg=colors["bg"],
            fg=colors["fg"],
        )

    def _start_timed_phase(
        self,
        duration: float,
        offset: float,
        on_done: Callable[[], None],
    ) -> None:
        self._phase_duration = duration
        self._phase_offset = offset
        self._phase_deadline = time.monotonic() + duration
        self._phase_done = on_done
        self._tick_timed_phase()

    def _tick_timed_phase(self) -> None:
        remaining = max(0.0, self._phase_deadline - time.monotonic())
        elapsed = self._phase_duration - remaining
        self.countdown.set(f"剩余 {remaining:.1f} 秒")
        self.progress.configure(value=self._phase_offset + elapsed)
        self._update_signal_status()
        if remaining <= 0:
            callback, self._phase_done = self._phase_done, None
            if callback is not None:
                callback()
            return
        self._schedule(100, self._tick_timed_phase)

    def _update_signal_status(self) -> None:
        if self._session is None:
            return
        summary = self._session.recorder_summary()
        labels = (("eeg", "EEG"), ("fnirs", "fNIRS"), ("motion", "Motion"))
        parts = [f"{label} {int((summary.get(kind) or {}).get('sample_count') or 0):,}" for kind, label in labels]
        self.signal_status.set("实时样本：" + " · ".join(parts))

    def _handle_space(self, _event: object) -> str:
        if self._session is None or not self._stimuli or self._trial_index >= len(self._stimuli):
            return "break"
        if self._trial_stimulus_timestamp is not None and self._trial_response_timestamp is None:
            self._trial_response_timestamp = self._session.clock_now()
        return "break"

    def _request_abort(self) -> None:
        if self._session is None:
            self._on_cancel()
            return
        if not messagebox.askyesno("确认中止", "将停止录制并保留已采集的原始数据，是否继续？", parent=self):
            return
        self._cancel_scheduled()
        session, self._session = self._session, None
        try:
            session.abort("operator_requested")
        except Exception as exc:
            messagebox.showerror("中止失败", str(exc), parent=self)
        self.unbind_all("<space>")
        self._on_cancel()

    def _schedule(self, milliseconds: int, callback: Callable[[], None]) -> None:
        token = ""

        def run() -> None:
            self._after_ids.discard(token)
            callback()

        token = self.after(milliseconds, run)
        self._after_ids.add(token)

    def _cancel_scheduled(self) -> None:
        for token in tuple(self._after_ids):
            try:
                self.after_cancel(token)
            except Exception:
                pass
        self._after_ids.clear()
