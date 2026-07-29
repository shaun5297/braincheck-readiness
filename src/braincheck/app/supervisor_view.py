from __future__ import annotations

from tkinter import StringVar, ttk


class SupervisorView(ttk.Frame):
    def __init__(self, parent: object, on_restart: object) -> None:
        super().__init__(parent, padding=24)
        self.title = StringVar(value="等待结果")
        self.detail = StringVar(value="")
        ttk.Label(self, textvariable=self.title, font=("", 26, "bold")).pack(anchor="w")
        ttk.Label(self, textvariable=self.detail, wraplength=640, justify="left").pack(anchor="w", pady=18)
        ttk.Label(self, text="结果只描述当次班次状态，不表示个人长期能力，也不构成自动化岗位决定。", wraplength=640).pack(anchor="w", pady=12)
        ttk.Button(self, text="返回首页", command=on_restart).pack(anchor="e")

    def show_result(self, payload: dict[str, object]) -> None:
        self.title.set(str(payload["label"]))
        reasons = "；".join(str(value) for value in payload.get("reason_text", ())) or "未发现达到复测条件的当次状态信号"
        self.detail.set(f"数据质量：{payload['data_quality']}\n主要原因：{reasons}\n建议动作：{payload['recommended_action']}")

