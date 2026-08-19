from __future__ import annotations

import tkinter as tk
from tkinter import StringVar, ttk

from .theme import FONT_FAMILY, STATUS_COLORS


class SupervisorView(ttk.Frame):
    def __init__(self, parent: object, on_restart: object) -> None:
        super().__init__(parent, padding=(24, 24))
        # 居中布局：左右留白列
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=620)
        self.columnconfigure(2, weight=1)

        # 大号状态徽章（通过/不通过等，醒目）
        self.badge = tk.Label(
            self,
            text="",
            font=(FONT_FAMILY, 34, "bold"),
            padx=40,
            pady=18,
        )
        self.badge.grid(row=0, column=1, pady=(6, 10))

        ttk.Label(self, text="当次班前认知准备度评估结果", style="Muted.TLabel").grid(
            row=1, column=1, pady=(0, 20)
        )

        card = ttk.Frame(self, style="Card.TFrame", padding=(30, 22))
        card.grid(row=2, column=1, sticky="ew")
        card.columnconfigure(1, weight=1)

        self.quality = StringVar(value="")
        self.reasons = StringVar(value="")
        self.action = StringVar(value="")
        self.confidence = StringVar(value="")
        rows = (
            ("数据质量", self.quality),
            ("主要原因", self.reasons),
            ("建议动作", self.action),
            ("置信度", self.confidence),
        )
        for index, (label, var) in enumerate(rows):
            ttk.Label(card, text=label, style="Section.TLabel").grid(
                row=index, column=0, sticky="nw", pady=9, padx=(0, 20)
            )
            ttk.Label(
                card,
                textvariable=var,
                style="Card.TLabel",
                wraplength=430,
                justify="left",
            ).grid(row=index, column=1, sticky="w", pady=9)

        ttk.Label(
            self,
            text="结果只描述当次班次状态，不表示个人长期能力，也不构成自动化岗位决定。",
            style="Muted.TLabel",
            wraplength=620,
        ).grid(row=3, column=1, pady=(20, 0))

        ttk.Button(
            self,
            text="返回首页",
            style="Accent.TButton",
            command=on_restart,
            takefocus=False,
        ).grid(row=4, column=1, pady=(24, 4), ipadx=16)

    def show_result(self, payload: dict[str, object], *, competition_demo: bool = False) -> None:
        status = str(payload.get("status", "unable"))
        colors = STATUS_COLORS.get(status, STATUS_COLORS["unable"])
        label = str(payload["label"])
        display = label if not (competition_demo and label != "无法评估") else f"{label}（演示）"
        self.badge.config(text=f"{colors['icon']}  {display}", bg=colors["bg"], fg=colors["fg"])
        reasons = (
            "；".join(str(value) for value in payload.get("reason_text", ()))
            or "未发现达到复测条件的当次状态信号"
        )
        notice = "\n结果声明：比赛功能演示占位，不代表真实受试状态结论。" if competition_demo else ""
        self.quality.set(str(payload.get("data_quality", "")))
        self.reasons.set(reasons)
        self.action.set(f"{payload.get('recommended_action', '')}{notice}")
        confidence = float(payload.get("confidence", 0.0))
        self.confidence.set(f"{confidence:.1%}")
