from __future__ import annotations

from tkinter import BooleanVar, DoubleVar, IntVar, StringVar, ttk


class ParticipantView(ttk.Frame):
    def __init__(self, parent: object, on_start: object) -> None:
        super().__init__(parent, padding=24)
        self.participant_id = StringVar(value="A001")
        self.kss = IntVar(value=3)
        self.sleep = DoubleVar(value=7.5)
        self.awake = DoubleVar(value=8)
        self.shift = StringVar(value="日班")
        self.discomfort = BooleanVar(value=False)
        self.voluntary = BooleanVar(value=True)
        ttk.Label(self, text="班前认知准备度评估", font=("", 22, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        ttk.Label(self, text="仅使用匿名工号；本系统不进行医疗诊断，也不自动决定是否上岗。", wraplength=620).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))
        fields = (
            ("匿名工号", ttk.Entry(self, textvariable=self.participant_id)),
            ("KSS（1-9）", ttk.Spinbox(self, from_=1, to=9, textvariable=self.kss)),
            ("过去24小时睡眠", ttk.Spinbox(self, from_=0, to=24, increment=0.5, textvariable=self.sleep)),
            ("连续清醒小时", ttk.Spinbox(self, from_=0, to=48, increment=0.5, textvariable=self.awake)),
            ("当前班次", ttk.Combobox(self, values=("日班", "夜班", "倒班/跨时段", "不适用"), textvariable=self.shift, state="readonly")),
        )
        for index, (label, widget) in enumerate(fields, 2):
            ttk.Label(self, text=label).grid(row=index, column=0, sticky="w", pady=5)
            widget.grid(row=index, column=1, sticky="ew", pady=5)
        ttk.Checkbutton(self, text="当前存在急性不适", variable=self.discomfort).grid(row=7, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(self, text="我已阅读隐私说明并自愿继续", variable=self.voluntary).grid(row=8, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Button(self, text="开始检测", command=on_start).grid(row=9, column=1, sticky="e", pady=18)
        self.columnconfigure(1, weight=1)

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

