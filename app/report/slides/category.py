"""4 カテゴリ別売上：カテゴリ別の売上・構成比・前年比（横棒グラフ＋表）"""

from __future__ import annotations

from pptx.presentation import Presentation
from pptx.util import Inches

from .. import builder
from ..metrics import ReportData


def build_category(prs: Presentation, data: ReportData) -> None:
    slide = builder.new_slide(prs, builder.LAYOUT_CONTENT, title="カテゴリ別売上")
    df = data.category.df

    categories = list(df["category"])
    amounts = [round(v / 1_000_000, 1) for v in df["amount"]]
    builder.add_bar_chart(
        slide, Inches(0.5), Inches(1.5), Inches(6.0), Inches(5.3), categories, {"売上（百万円）": amounts}
    )

    headers = ["カテゴリ", "売上（百万円）", "構成比", "前年比"]
    rows = []
    for row in df.itertuples():
        rows.append(
            [
                row.category,
                builder.fmt_millions(row.amount),
                builder.fmt_percent(row.share),
                builder.fmt_percent(row.yoy_ratio, signed=True),
            ]
        )

    def color_fn(row_idx, col_idx, raw_row):
        if col_idx == 3:
            return builder.ratio_color(df.iloc[row_idx]["yoy_ratio"])
        return None

    builder.add_table(
        slide, Inches(6.8), Inches(1.5), Inches(6.0), Inches(5.3), headers, rows, font_color_fn=color_fn
    )

    builder.set_notes(slide, month=data.month, region=data.region, generated_at=data.generated_at)
