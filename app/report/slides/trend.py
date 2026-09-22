"""3 売上推移：直近12か月の売上と前年同期（折れ線グラフ・2系列）"""

from __future__ import annotations

import pandas as pd
from pptx.presentation import Presentation
from pptx.util import Inches

from .. import builder
from ..metrics import ReportData


def _to_millions(v) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v) / 1_000_000, 1)


def build_trend(prs: Presentation, data: ReportData) -> None:
    slide = builder.new_slide(prs, builder.LAYOUT_CONTENT, title="売上推移")
    df = data.trend.df

    categories = [f"{m:%Y-%m}" for m in df["month"]]
    series = {
        "当期": [_to_millions(v) for v in df["amount"]],
        "前年同期": [_to_millions(v) for v in df["amount_prev_year"]],
    }

    builder.add_line_chart(slide, Inches(0.5), Inches(1.6), Inches(12.3), Inches(5.3), categories, series)

    builder.set_notes(slide, month=data.month, region=data.region, generated_at=data.generated_at)
