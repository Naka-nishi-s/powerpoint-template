"""所見コメント生成（ルールベース）。

`generate_insights(data) -> list[str]` というインターフェースで切り出してあるため、
将来はLLMに集計結果（数値のみ）を渡して文章を生成する実装に差し替えられる。
"""

from __future__ import annotations

from .metrics import ReportData

# 閾値はここに定数としてまとめ、あとから調整できるようにする
CATEGORY_YOY_THRESHOLD = 0.10  # ±10%を超えるカテゴリ前年比
STORE_ACHIEVEMENT_THRESHOLD = 0.90  # 達成率90%未満の店舗
EC_SHARE_DELTA_THRESHOLD = 0.02  # EC構成比が前年から2ポイント以上変動
GROSS_MARGIN_DELTA_THRESHOLD = 0.01  # 粗利率が前月から1ポイント以上変動
MAX_INSIGHTS = 5


def generate_insights(data: ReportData) -> list[str]:
    """ReportDataから所見文を最大MAX_INSIGHTS件、重要度の高い順に生成する。"""
    candidates: list[tuple[float, str]] = []

    summary = data.summary
    category = data.category
    store = data.store

    if summary is not None and summary.achievement_ratio is not None:
        pct = summary.achievement_ratio * 100
        if summary.achievement_ratio >= 1.0:
            candidates.append((90, f"全体の予算達成率は{pct:.1f}％で、予算を達成した。"))
        else:
            candidates.append((95, f"全体の予算達成率は{pct:.1f}％で、予算を下回った。"))

    if category is not None:
        for row in category.df.itertuples():
            if row.yoy_ratio is not None and abs(row.yoy_ratio) > CATEGORY_YOY_THRESHOLD:
                direction = "伸びた" if row.yoy_ratio > 0 else "落ち込んだ"
                importance = 80 + min(abs(row.yoy_ratio) * 100, 15)
                candidates.append(
                    (importance, f"{row.category}カテゴリが前年比{row.yoy_ratio * 100:+.1f}％と{direction}。")
                )

    if store is not None:
        under = store.df[store.df["achievement_ratio"] < STORE_ACHIEVEMENT_THRESHOLD]
        for row in under.itertuples():
            candidates.append(
                (85, f"{row.store_name}は達成率{row.achievement_ratio * 100:.1f}％で要確認。")
            )

        if store.ec_share is not None and store.ec_share_prev_year is not None:
            delta = store.ec_share - store.ec_share_prev_year
            if abs(delta) >= EC_SHARE_DELTA_THRESHOLD:
                direction = "上昇" if delta > 0 else "低下"
                candidates.append(
                    (
                        70,
                        f"EC比率が前年の{store.ec_share_prev_year * 100:.1f}％から"
                        f"{store.ec_share * 100:.1f}％に{direction}。",
                    )
                )

    if (
        summary is not None
        and summary.gross_margin is not None
        and summary.prev_month_gross_margin is not None
    ):
        delta = summary.gross_margin - summary.prev_month_gross_margin
        if abs(delta) >= GROSS_MARGIN_DELTA_THRESHOLD:
            candidates.append((60, f"粗利率が前月比{delta * 100:+.1f}ポイント。"))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in candidates[:MAX_INSIGHTS]]
