from __future__ import annotations

from pathlib import Path
from tkinter import StringVar, Tk, ttk

from ..reports.participant import build as participant_report
from ..workflow.screening import ScreeningService, demo_payload
from .debug_view import DebugView
from .operator_view import OperatorView
from .participant_view import ParticipantView
from .router import Router
from .supervisor_view import SupervisorView


class BrainCheckApp:
    def __init__(self, root: Tk, *, data_root: Path, demo: bool, scenario: str, debug: bool) -> None:
        self.root = root
        self.service = ScreeningService(data_root)
        self.demo = demo
        self.scenario = scenario
        self.sequence = 0
        root.title("脑安检 - BrainCheck Readiness")
        root.geometry("760x650")
        header = ttk.Frame(root, padding=(16, 10))
        header.pack(fill="x")
        ttk.Label(header, text="脑安检", font=("", 18, "bold")).pack(side="left")
        self.badge = StringVar(value="演示模式" if demo else "正式模式")
        ttk.Label(header, textvariable=self.badge).pack(side="right")
        self.router = Router(root)
        self.router.pack(fill="both", expand=True)
        self.participant = ParticipantView(self.router, self.start)
        self.operator = OperatorView(self.router, self.complete)
        self.result = SupervisorView(self.router, self.restart)
        self.router.add("participant", self.participant)
        self.router.add("operator", self.operator)
        self.router.add("result", self.result)
        self.debug_view = DebugView(self.router) if debug else None
        if self.debug_view:
            self.router.add("debug", self.debug_view)
        self.router.show("participant")

    def start(self) -> None:
        values = self.participant.values()
        if not values["participant_id"] or not values["voluntary"]:
            self.badge.set("请确认匿名工号与自愿继续")
            return
        self.router.show("operator")

    def complete(self) -> None:
        self.sequence += 1
        features, quality = demo_payload(self.scenario if self.demo else "normal")
        values = self.participant.values()
        features.context.update({
            "kss": values["kss"],
            "sleep_hours_24h": values["sleep_hours_24h"],
            "continuous_awake_hours": values["continuous_awake_hours"],
            "shift": values["shift"],
        })
        result = self.service.assess(str(values["participant_id"]), features, quality, sequence=self.sequence)
        self.result.show_result(participant_report(result, personal_baseline_available=False))
        if self.debug_view:
            self.debug_view.update_payload({"result": result.to_dict(), "features": features.to_dict(), "quality": quality.to_dict()})
        self.router.show("result")

    def restart(self) -> None:
        self.router.show("participant")


def run(*, data_root: Path, demo: bool = False, scenario: str = "normal", debug: bool = False) -> None:
    root = Tk()
    BrainCheckApp(root, data_root=data_root, demo=demo, scenario=scenario, debug=debug)
    root.mainloop()

