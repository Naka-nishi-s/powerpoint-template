"""Streamlit画面（入口）"""

from __future__ import annotations

import logging
from datetime import date

import streamlit as st

from report import builder, queries
from report.db import get_engine
from report.generate import build_filename, generate_report, generate_slide
from report.insights import generate_insights
from report.metrics import ReportData, build_report_data
from report.slides import SLIDE_DATA_SECTIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sales_report")

st.set_page_config(page_title="月次売上レポート自動生成ツール", layout="wide")

SLIDE_LABELS = {
    "cover": "表紙",
    "summary": "サマリー",
    "trend": "売上推移",
    "category": "カテゴリ別売上",
    "store": "地域・店舗別実績",
    "product": "商品ランキング",
    "customer": "顧客分析",
    "insights": "所見・課題",
}
TAB_A_SLIDES = list(SLIDE_LABELS.keys())  # パターンA：8種類から1つ
TAB_B_OPTIONAL_SLIDES = [s for s in SLIDE_LABELS if s not in ("cover", "summary")]  # 3〜8


@st.cache_data(ttl=600)
def cached_months(_engine) -> list[date]:
    return queries.fetch_available_months(_engine)


@st.cache_data(ttl=600)
def cached_regions(_engine) -> list[str]:
    return queries.fetch_regions(_engine)


@st.cache_data(ttl=600)
def cached_report_data(_engine, month: date, region: str | None, sections: tuple[str, ...]) -> ReportData:
    return build_report_data(_engine, month, region, set(sections))


def _reset_downloads() -> None:
    for k in ("tabA_bytes", "tabA_filename", "tabB_bytes", "tabB_filename"):
        st.session_state.pop(k, None)


def _render_preview(slide_id: str, data: ReportData) -> None:
    if slide_id == "summary" and data.summary is not None:
        s = data.summary
        cols = st.columns(5)
        cols[0].metric("売上（百万円）", builder.fmt_millions(s.amount))
        cols[1].metric("粗利（百万円）", builder.fmt_millions(s.gross_profit))
        cols[2].metric("前月比", builder.fmt_percent(s.mom_ratio, signed=True))
        cols[3].metric("前年同月比", builder.fmt_percent(s.yoy_ratio, signed=True))
        cols[4].metric("予算達成率", builder.fmt_percent(s.achievement_ratio))

    if slide_id == "trend" and data.trend is not None:
        df = data.trend.df.set_index("month")[["amount", "amount_prev_year"]]
        df = df.rename(columns={"amount": "当期", "amount_prev_year": "前年同期"})
        st.line_chart(df)

    if slide_id == "category" and data.category is not None:
        st.dataframe(data.category.df, hide_index=True)

    if slide_id == "store" and data.store is not None:
        st.dataframe(data.store.df, hide_index=True)

    if slide_id == "product" and data.product is not None:
        st.dataframe(data.product.top10, hide_index=True)

    if slide_id == "customer" and data.customer is not None:
        st.dataframe(data.customer.by_type, hide_index=True)

    if slide_id == "insights" and data.summary is not None:
        for text in generate_insights(data):
            st.write(f"- {text}")


def _render_tab_a(engine, month: date, region: str | None) -> None:
    slide_id = st.radio(
        "スライド", options=TAB_A_SLIDES, format_func=lambda s: SLIDE_LABELS[s], index=1, key="tabA_slide"
    )

    if slide_id == "cover":
        st.info("表紙にはプレビューする数値はありません。")
    else:
        try:
            sections = tuple(sorted(SLIDE_DATA_SECTIONS[slide_id]))
            data = cached_report_data(engine, month, region, sections)
        except Exception:
            logger.exception("failed to build preview data")
            st.error("レポートの生成に失敗しました。")
            return
        _render_preview(slide_id, data)

    if st.button("生成", key="tabA_generate"):
        with st.spinner("生成中..."):
            try:
                content = generate_slide(month, slide_id, region, engine=engine)
                st.session_state["tabA_bytes"] = content
                st.session_state["tabA_filename"] = build_filename(month, slide_id=slide_id, region=region)
            except Exception:
                logger.exception("failed to generate slide")
                st.error("レポートの生成に失敗しました。")

    if "tabA_bytes" in st.session_state:
        st.download_button(
            "ダウンロード",
            data=st.session_state["tabA_bytes"],
            file_name=st.session_state["tabA_filename"],
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="tabA_download",
        )


def _render_tab_b(engine, month: date, region: str | None) -> None:
    selected = st.multiselect(
        "含めるスライド（表紙・サマリーは常に出力）",
        options=TAB_B_OPTIONAL_SLIDES,
        default=TAB_B_OPTIONAL_SLIDES,
        format_func=lambda s: SLIDE_LABELS[s],
        key="tabB_slides",
    )
    with_insights = st.checkbox("所見を自動生成", value=True, key="tabB_insights")

    try:
        data = cached_report_data(engine, month, region, ("summary", "trend"))
    except Exception:
        logger.exception("failed to build preview data")
        st.error("レポートの生成に失敗しました。")
        return
    _render_preview("summary", data)
    _render_preview("trend", data)

    if st.button("生成", key="tabB_generate"):
        with st.spinner("生成中..."):
            try:
                content = generate_report(
                    month, region, ["cover", "summary"] + selected, with_insights, engine=engine
                )
                st.session_state["tabB_bytes"] = content
                st.session_state["tabB_filename"] = build_filename(month, region=region)
            except Exception:
                logger.exception("failed to generate report")
                st.error("レポートの生成に失敗しました。")

    if "tabB_bytes" in st.session_state:
        st.download_button(
            "ダウンロード",
            data=st.session_state["tabB_bytes"],
            file_name=st.session_state["tabB_filename"],
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="tabB_download",
        )


def main() -> None:
    engine = get_engine()

    try:
        months = cached_months(engine)
        regions = cached_regions(engine)
    except Exception:
        logger.exception("failed to load months/regions")
        st.error("データの取得に失敗しました。")
        return

    if not months:
        st.warning("対象データがありません。")
        return

    st.title("月次売上レポート自動生成ツール")

    with st.sidebar:
        st.header("条件")
        month = st.selectbox(
            "対象月",
            options=list(reversed(months)),
            format_func=lambda d: f"{d:%Y-%m}",
            key="month",
            on_change=_reset_downloads,
        )
        region_label = st.selectbox(
            "拠点",
            options=["全体"] + regions,
            key="region",
            on_change=_reset_downloads,
        )
    region = None if region_label == "全体" else region_label

    tab_a, tab_b = st.tabs(["1ページずつ出力", "一括出力"])
    with tab_a:
        _render_tab_a(engine, month, region)
    with tab_b:
        _render_tab_b(engine, month, region)


main()
