"""5 地域・店舗別実績：店舗別の売上・予算・達成率（達成率の高い順、未達は赤）"""

from __future__ import annotations

from pptx.presentation import Presentation
from pptx.util import Inches

from .. import builder
from ..metrics import ReportData


def build_store(prs: Presentation, data: ReportData) -> None:
    slide = builder.new_slide(prs, builder.LAYOUT_CONTENT, title="地域・店舗別実績")
    df = data.store.df

    headers = ["店舗", "地域", "チャネル", "売上（百万円）", "予算（百万円）", "達成率"]
    rows = []
    for row in df.itertuples():
        rows.append(
            [
                row.store_name,
                row.region,
                row.channel,
                builder.fmt_millions(row.amount),
                builder.fmt_millions(row.target_amount),
                builder.fmt_percent(row.achievement_ratio),
            ]
        )

    def color_fn(row_idx, col_idx, raw_row):
        if col_idx == 5:
            return builder.achievement_color(df.iloc[row_idx]["achievement_ratio"])
        return None

    builder.add_table(
        slide, Inches(0.5), Inches(1.5), Inches(12.3), Inches(5.3), headers, rows, font_color_fn=color_fn
    )

    builder.set_notes(slide, month=data.month, region=data.region, generated_at=data.generated_at)
