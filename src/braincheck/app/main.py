from __future__ import annotations

from pathlib import Path
from tkinter import StringVar, Tk, ttk

from ..reports.participant import build as participant_report
from ..workflow.live_screening import LiveScreeningOutcome
from ..workflow.screening import ScreeningService, demo_payload
from .debug_view import DebugView
from .operator_view import OperatorView
from .participant_view import ParticipantView
from .router import Router
from .supervisor_view import SupervisorView


class BrainCheckApp:
    def __init__(
        self,
        root: Tk,
        *,
        data_root: Path,
        demo: bool,
        competition_demo: bool,
        scenario: str,
        debug: bool,
    ) -> None:
        self.root = root
        self.data_root = data_root
        self.service = ScreeningService(data_root)
        self.demo = demo
        self.competition_demo = competition_demo
        self.scenario = scenario
        self.sequence = 0
        root.title("脑安检 - BrainCheck Readiness")
        root.geometry("760x650")
        header = ttk.Frame(root, padding=(16, 10))
        header.pack(fill="x")
        ttk.Label(header, text="脑安检", font=("", 18, "bold")).pack(side="left")
        mode_label = "合成演示模式" if demo else ("比赛演示模式" if competition_demo else "正式模式")
        self.badge = StringVar(value=mode_label)
        ttk.Label(header, textvariable=self.badge).pack(side="right")
        self.router = Router(root)
        self.router.pack(fill="both", expand=True)
        self.participant = ParticipantView(self.router, self.start)
        self.operator = OperatorView(
            self.router,
            on_live_complete=self.complete_live,
            on_demo_complete=self.complete_demo,
            on_cancel=self.restart,
        )
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
        if values["acute_discomfort"]:
            self.badge.set("存在急性不适，请停止检测并人工处理")
            return
        self.sequence = max(
            self.sequence + 1,
            self.service.next_sequence(str(values["participant_id"])),
        )
        self.router.show("operator")
        self.operator.begin(
            data_root=self.data_root,
            participant_id=str(values["participant_id"]),
            sequence=self.sequence,
            context=self._context(values),
            synthetic_demo=self.demo,
        )

    def complete_demo(self) -> None:
        features, quality = demo_payload(self.scenario)
        values = self.participant.values()
        features.context.update(self._context(values))
        result = self.service.assess(str(values["participant_id"]), features, quality, sequence=self.sequence)
        self.result.show_result(participant_report(result, personal_baseline_available=False))
        if self.debug_view:
            self.debug_view.update_payload({"result": result.to_dict(), "features": features.to_dict(), "quality": quality.to_dict()})
        self.router.show("result")

    def complete_live(self, outcome: LiveScreeningOutcome) -> None:
        values = self.participant.values()
        outcome.features.metadata["competition_demo"] = self.competition_demo
        result = self.service.assess(
            str(values["participant_id"]),
            outcome.features,
            outcome.quality,
            sequence=self.sequence,
            competition_demo=self.competition_demo,
        )
        self.result.show_result(
            participant_report(result, personal_baseline_available=False),
            competition_demo=result.algorithm_version == "competition_demo_placeholder_v1",
        )
        if self.debug_view:
            self.debug_view.update_payload(
                {
                    "result": result.to_dict(),
                    "features": outcome.features.to_dict(),
                    "quality": outcome.quality.to_dict(),
                    "capture_directory": str(outcome.capture_directory),
                    "raw_xdf": str(outcome.raw_xdf),
                }
            )
        self.router.show("result")

    @staticmethod
    def _context(values: dict[str, object]) -> dict[str, object]:
        return {
            "kss": values["kss"],
            "sleep_hours_24h": values["sleep_hours_24h"],
            "continuous_awake_hours": values["continuous_awake_hours"],
            "shift": values["shift"],
            "acute_discomfort": values["acute_discomfort"],
        }

    def restart(self) -> None:
        self.router.show("participant")


def run(
    *,
    data_root: Path,
    demo: bool = False,
    competition_demo: bool = False,
    scenario: str = "normal",
    debug: bool = False,
) -> None:
    root = Tk()
    BrainCheckApp(
        root,
        data_root=data_root,
        demo=demo,
        competition_demo=competition_demo,
        scenario=scenario,
        debug=debug,
    )
    root.mainloop()
