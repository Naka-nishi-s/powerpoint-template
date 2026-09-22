"""2 サマリー：売上、粗利、前月比、前年同月比、予算達成率、要点3行"""

from __future__ import annotations

from pptx.presentation import Presentation
from pptx.util import Inches

from .. import builder
from ..metrics import ReportData


def _bullets(data: ReportData) -> list[str]:
    s = data.summary
    lines: list[str] = []
    if s.achievement_ratio is not None:
        verb = "達成した" if s.achievement_ratio >= 1.0 else "下回った"
        lines.append(f"予算達成率は{builder.fmt_percent(s.achievement_ratio)}で、予算を{verb}。")
    if s.mom_ratio is not None:
        lines.append(f"売上は前月比{builder.fmt_percent(s.mom_ratio, signed=True)}。")
    if s.yoy_ratio is not None:
        lines.append(f"売上は前年同月比{builder.fmt_percent(s.yoy_ratio, signed=True)}。")
    return lines[:3]


def build_summary(prs: Presentation, data: ReportData) -> None:
    slide = builder.new_slide(prs, builder.LAYOUT_CONTENT, title="サマリー")
    s = data.summary

    card_w = Inches(2.4)
    card_h = Inches(1.5)
    top = Inches(1.6)
    gap = Inches(0.15)

    cards = [
        ("売上（百万円）", builder.fmt_millions(s.amount), None),
        ("粗利（百万円）", builder.fmt_millions(s.gross_profit), None),
        ("前月比", builder.fmt_percent(s.mom_ratio, signed=True), builder.ratio_color(s.mom_ratio)),
        ("前年同月比", builder.fmt_percent(s.yoy_ratio, signed=True), builder.ratio_color(s.yoy_ratio)),
        ("予算達成率", builder.fmt_percent(s.achievement_ratio), builder.achievement_color(s.achievement_ratio)),
    ]
    left = Inches(0.5)
    for label, value, color in cards:
        builder.add_kpi_card(slide, left, top, card_w, card_h, label, value, value_color=color)
        left += card_w + gap

    builder.add_bullets(
        slide, Inches(0.5), Inches(3.4), Inches(12.3), Inches(2.5), _bullets(data), font_size=18
    )

    builder.set_notes(slide, month=data.month, region=data.region, generated_at=data.generated_at)
