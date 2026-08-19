from __future__ import annotations

import tkinter as tk
from tkinter import BooleanVar, DoubleVar, IntVar, StringVar, ttk

from .theme import BG, DANGER, FONT_FAMILY


class ParticipantView(ttk.Frame):
    def __init__(self, parent: object, on_start: object) -> None:
        super().__init__(parent, padding=(24, 16))
        self.participant_id = StringVar(value="A001")
        self.kss = IntVar(value=3)
        self.sleep = DoubleVar(value=7.5)
        self.awake = DoubleVar(value=8)
        self.shift = StringVar(value="日班")
        self.discomfort = BooleanVar(value=False)
        self.voluntary = BooleanVar(value=True)

        # 居中布局：左右留白列，内容集中在中间
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=580)
        self.columnconfigure(2, weight=1)

        ttk.Label(self, text="班前认知准备度评估", style="Title.TLabel").grid(
            row=0, column=1, pady=(4, 6)
        )
        ttk.Label(
            self,
            text="仅使用匿名工号；本系统不进行医疗诊断，也不自动决定是否上岗。",
            style="Muted.TLabel",
        ).grid(row=1, column=1, pady=(0, 18))

        card = ttk.Frame(self, style="Card.TFrame", padding=(28, 22))
        card.grid(row=2, column=1, sticky="ew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="受试者信息", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )
        fields = (
            ("匿名工号", ttk.Entry(card, textvariable=self.participant_id, width=26)),
            ("KSS（1-9）", ttk.Spinbox(card, from_=1, to=9, textvariable=self.kss, width=26)),
            (
                "过去24小时睡眠（小时）",
                ttk.Spinbox(card, from_=0, to=24, increment=0.5, textvariable=self.sleep, width=26),
            ),
            (
                "连续清醒小时",
                ttk.Spinbox(card, from_=0, to=48, increment=0.5, textvariable=self.awake, width=26),
            ),
            (
                "当前班次",
                ttk.Combobox(
                    card,
                    values=("日班", "夜班", "倒班/跨时段", "不适用"),
                    textvariable=self.shift,
                    state="readonly",
                    width=24,
                ),
            ),
        )
        for index, (label, widget) in enumerate(fields, 1):
            ttk.Label(card, text=label, style="Card.TLabel").grid(
                row=index, column=0, sticky="w", pady=7
            )
            widget.grid(row=index, column=1, sticky="ew", pady=7)

        ttk.Separator(card, orient="horizontal").grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky="ew", pady=(14, 10)
        )
        ttk.Checkbutton(card, text="当前存在急性不适", variable=self.discomfort).grid(
            row=len(fields) + 2, column=0, columnspan=2, sticky="w", pady=4
        )
        ttk.Checkbutton(card, text="我已阅读隐私说明并自愿继续", variable=self.voluntary).grid(
            row=len(fields) + 3, column=0, columnspan=2, sticky="w", pady=4
        )

        self.error = StringVar(value="")
        tk.Label(
            self,
            textvariable=self.error,
            font=(FONT_FAMILY, 13, "bold"),
            fg=DANGER,
            bg=BG,
        ).grid(row=3, column=1, pady=(14, 0))

        ttk.Button(
            self,
            text="开始检测",
            style="Accent.TButton",
            command=on_start,
            takefocus=False,
        ).grid(row=4, column=1, pady=(18, 4), ipadx=16)

    def set_error(self, message: str) -> None:
        self.error.set(message)

    def values(self) -> dict[str, object]:
        return {
            "participant_id": self.participant_id.get().strip(),
            "kss": self.kss.get(),
            "sleep_hours_24h": self.sleep.get(),
            "continuous_awake_hours": self.awake.get(),
            "shift": self.shift.get(),
            "acute_discomfort": self.discomfort.get(),
            "voluntary": self.voluntary.get(),
        }


