"""7 顧客分析：新規・既存の売上比率、顧客区分別売上、客単価（円グラフ＋KPI）"""

from __future__ import annotations

from pptx.presentation import Presentation
from pptx.util import Inches

from .. import builder
from ..metrics import ReportData


def build_customer(prs: Presentation, data: ReportData) -> None:
    slide = builder.new_slide(prs, builder.LAYOUT_CONTENT, title="顧客分析")
    c = data.customer

    builder.add_pie_chart(
        slide,
        Inches(0.5),
        Inches(1.5),
        Inches(5.5),
        Inches(4.5),
        ["新規", "既存"],
        [round(c.new_amount / 1_000_000, 1), round(c.existing_amount / 1_000_000, 1)],
    )

    builder.add_kpi_card(
        slide,
        Inches(6.5),
        Inches(1.5),
        Inches(2.8),
        Inches(1.4),
        "客単価（円）",
        f"{c.unit_price:,.0f}" if c.unit_price is not None else builder.DASH,
    )
    builder.add_kpi_card(
        slide,
        Inches(9.5),
        Inches(1.5),
        Inches(2.8),
        Inches(1.4),
        "購入顧客数",
        f"{c.customer_count:,}",
    )

    headers = ["顧客区分", "売上（百万円）", "構成比"]
    rows = [
        [row.customer_type, builder.fmt_millions(row.amount), builder.fmt_percent(row.share)]
        for row in c.by_type.itertuples()
    ]
    builder.add_table(slide, Inches(6.5), Inches(3.2), Inches(5.8), Inches(2.0), headers, rows)

    builder.set_notes(slide, month=data.month, region=data.region, generated_at=data.generated_at)
