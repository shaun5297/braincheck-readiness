from __future__ import annotations

from tkinter import ttk


class Router(ttk.Frame):
    def __init__(self, parent: object) -> None:
        super().__init__(parent)
        self._pages: dict[str, ttk.Frame] = {}

    def add(self, name: str, page: ttk.Frame) -> None:
        self._pages[name] = page
        page.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def show(self, name: str) -> None:
        self._pages[name].tkraise()

