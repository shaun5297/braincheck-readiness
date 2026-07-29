from __future__ import annotations

import json
from tkinter import Text, ttk


class DebugView(ttk.Frame):
    def __init__(self, parent: object) -> None:
        super().__init__(parent, padding=16)
        ttk.Label(self, text="调试端（受限）", font=("", 18, "bold")).pack(anchor="w")
        self.text = Text(self, height=24, width=90)
        self.text.pack(fill="both", expand=True, pady=10)

    def update_payload(self, payload: dict[str, object]) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))

