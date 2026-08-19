"""GUI 层回归测试。

覆盖 bug: SART 任务中按空格误触有焦点的 ttk.Button, 导致流程被重置回
"信号质量检查" 界面。

根因: ttk.Button 有焦点时, 空格键会先被按钮 class 绑定激活 (bindtags 顺序
widget -> class -> toplevel -> all), 而 OperatorView 用 bind_all 绑定的
_handle_space 位于 all 层, 返回 "break" 已经太晚, 无法阻止按钮激活。

修复: 所有按钮 takefocus=False (点击/Tab 都不会让按钮获得键盘焦点),
begin() 时把焦点移到 OperatorView 本身。
"""
import unittest

try:
    from tkinter import Tk, ttk

    _TK_OK = True
except Exception:  # pragma: no cover - 无 Tk 环境
    _TK_OK = False

from braincheck.app.main import BrainCheckApp
from braincheck.app.operator_view import OperatorView


def _find_buttons(widget: ttk.Widget) -> list[ttk.Button]:
    buttons: list[ttk.Button] = []
    for child in widget.winfo_children():
        if isinstance(child, ttk.Button):
            buttons.append(child)
        buttons.extend(_find_buttons(child))
    return buttons


@unittest.skipUnless(_TK_OK, "tkinter 不可用")
class ButtonFocusRegressionTests(unittest.TestCase):
    def test_all_buttons_do_not_take_keyboard_focus(self) -> None:
        """所有操作按钮不应获得键盘焦点, 否则空格/回车会误触按钮。"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            root = Tk()
            try:
                app = BrainCheckApp(
                    root,
                    data_root=Path(directory),
                    demo=True,
                    competition_demo=False,
                    scenario="normal",
                    debug=False,
                )
                root.update()
                buttons = (
                    _find_buttons(app.participant)
                    + _find_buttons(app.operator)
                    + _find_buttons(app.result)
                )
                self.assertTrue(buttons, "应能找到所有按钮")
                for button in buttons:
                    self.assertEqual(
                        button.cget("takefocus"),
                        0,
                        f"按钮 {button.cget('text')!r} 不应接收键盘焦点",
                    )
            finally:
                root.destroy()

    def test_begin_moves_focus_away_from_start_button(self) -> None:
        """begin() 后焦点应离开"开始检测"按钮, 防止 SART 空格误触发。"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            root = Tk()
            try:
                app = BrainCheckApp(
                    root,
                    data_root=Path(directory),
                    demo=True,
                    competition_demo=False,
                    scenario="normal",
                    debug=False,
                )
                root.update()
                start_button = next(
                    b for b in _find_buttons(app.participant) if b.cget("text") == "开始检测"
                )
                # 模拟点击"开始检测"后焦点残留的情况
                start_button.focus_set()
                root.update()
                app.participant.voluntary.set(True)
                app.participant.participant_id.set("A001")
                app.start()
                root.update()
                self.assertIs(root.focus_get(), app.operator)
            finally:
                root.destroy()


@unittest.skipUnless(_TK_OK, "tkinter 不可用")
class OperatorViewConstructionTests(unittest.TestCase):
    def test_operator_buttons_are_configured_without_focus(self) -> None:
        root = Tk()
        try:
            view = OperatorView(
                root,
                on_live_complete=lambda outcome: None,
                on_demo_complete=lambda: None,
                on_cancel=lambda: None,
            )
            self.assertEqual(view.cancel_button.cget("takefocus"), 0)
            self.assertEqual(view.action_button.cget("takefocus"), 0)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
