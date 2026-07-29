from __future__ import annotations

from tkinter import StringVar, ttk


class OperatorView(ttk.Frame):
    def __init__(self, parent: object, on_complete: object) -> None:
        super().__init__(parent, padding=24)
        self.status = StringVar(value="正在检查设备连接与佩戴稳定性…")
        ttk.Label(self, text="设备与任务", font=("", 22, "bold")).pack(anchor="w")
        ttk.Label(self, textvariable=self.status, wraplength=640).pack(anchor="w", pady=18)
        for value in ("脑电信号：良好", "额区光学信号：良好", "佩戴稳定性：良好"):
            ttk.Label(self, text=value, font=("", 14)).pack(anchor="w", pady=5)
        ttk.Label(self, text="正式流程将依次执行 30 秒质检、45 秒睁眼基线和 3 分钟 SART。").pack(anchor="w", pady=18)
        ttk.Button(self, text="完成演示采集", command=on_complete).pack(anchor="e")

