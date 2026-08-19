from __future__ import annotations

from tkinter import Tk, ttk

# ── 调色板 ────────────────────────────────────────────────────────────────────
BG = "#F2F5FA"            # 应用主背景（浅灰蓝）
CARD = "#FFFFFF"          # 卡片背景（白）
HEADER_BG = "#FFFFFF"     # 顶栏背景
BORDER = "#E2E8F0"        # 分隔线 / 边框
PRIMARY = "#2456A6"       # 品牌深蓝
PRIMARY_DARK = "#1B4385"  # 品牌深蓝（hover）
PRIMARY_BG = "#EAF1FC"    # 品牌浅蓝底
TEXT = "#1F2937"          # 主文字
TEXT_MUTED = "#64748B"    # 次要文字
DANGER = "#B91C1C"        # 危险红

# 结果状态配色（通过 / 复测 / 休息 / 无法评估）
STATUS_COLORS: dict[str, dict[str, str]] = {
    "normal": {"bg": "#E7F6EC", "fg": "#157F4A", "icon": "✓"},
    "retest": {"bg": "#FFF4E5", "fg": "#B45309", "icon": "▲"},
    "rest": {"bg": "#FDEBEC", "fg": "#B91C1C", "icon": "✕"},
    "unable": {"bg": "#EEF1F6", "fg": "#52606D", "icon": "—"},
}

# 任务阶段徽章配色
PHASE_COLORS: dict[str, dict[str, str]] = {
    "quality": {"bg": "#EAF1FC", "fg": "#2456A6"},
    "baseline": {"bg": "#E7F6EC", "fg": "#157F4A"},
    "sart": {"bg": "#F3E8FF", "fg": "#7C3AED"},
    "processing": {"bg": "#EEF1F6", "fg": "#52606D"},
}

# 在 macOS 上优先使用苹方字体；不存在时 Tk 会自动回退
FONT_FAMILY = "PingFang SC"


def setup_style(root: Tk) -> ttk.Style:
    """配置全局 ttk 主题与自定义样式。"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", background=BG, foreground=TEXT, font=(FONT_FAMILY, 13))
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Header.TFrame", background=HEADER_BG)

    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Header.TLabel", background=HEADER_BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Muted.TLabel", background=BG, foreground=TEXT_MUTED)
    style.configure("CardMuted.TLabel", background=CARD, foreground=TEXT_MUTED)
    style.configure("Title.TLabel", background=BG, foreground=PRIMARY, font=(FONT_FAMILY, 26, "bold"))
    style.configure("CardTitle.TLabel", background=CARD, foreground=TEXT, font=(FONT_FAMILY, 19, "bold"))
    style.configure("Section.TLabel", background=CARD, foreground=TEXT_MUTED, font=(FONT_FAMILY, 12, "bold"))

    style.configure("TEntry", fieldbackground=CARD, bordercolor=BORDER, padding=6)
    style.configure("TSpinbox", fieldbackground=CARD, bordercolor=BORDER, padding=6)
    style.configure("TCombobox", fieldbackground=CARD, bordercolor=BORDER, padding=6)
    style.configure("TCheckbutton", background=CARD, foreground=TEXT, font=(FONT_FAMILY, 13))

    style.configure("TButton", padding=(14, 8), font=(FONT_FAMILY, 13))
    style.configure("Accent.TButton", background=PRIMARY, foreground="#FFFFFF", font=(FONT_FAMILY, 14, "bold"), padding=(20, 10), borderwidth=0)
    style.map("Accent.TButton", background=[("active", PRIMARY_DARK), ("disabled", "#A9C3E9")])
    style.configure("Danger.TButton", foreground=DANGER)

    style.configure("TProgressbar", background=PRIMARY, troughcolor=BORDER, borderwidth=0, thickness=18)
    style.configure("TSeparator", background=BORDER)
    return style
