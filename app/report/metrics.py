"""集計・前年比・達成率 → ReportData。pandasのみに依存し、DBもpptxも知らない。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd
from sqlalchemy import Engine

from . import queries

# ReportDataが持つセクション名（generate.pyがどのクエリを実行するか決めるのに使う）
SECTIONS = ("summary", "trend", "category", "store", "product", "customer")

# 所見スライドが参照するセクション（6.5：所見は全データを使う）
INSIGHT_SECTIONS = ("summary", "category", "store")


def month_add(d: date, months: int) -> date:
    total = d.year * 12 + (d.month - 1) + months
    y, m = divmod(total, 12)
    return date(y, m + 1, 1)


def prev_month(d: date) -> date:
    return month_add(d, -1)


def prev_year_month(d: date) -> date:
    return month_add(d, -12)


def safe_div(numerator, denominator) -> float | None:
    if numerator is None or denominator is None:
        return None
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _row(df: pd.DataFrame, month: date) -> pd.Series | None:
    match = df[df["month"] == month]
    if match.empty:
        return None
    return match.iloc[0]


@dataclass
class SummaryData:
    amount: int
    gross_profit: int
    gross_margin: float | None
    prev_month_gross_margin: float | None
    mom_ratio: float | None
    yoy_ratio: float | None
    target_amount: int | None
    achievement_ratio: float | None


@dataclass
class TrendData:
    df: pd.DataFrame  # columns: month, amount, amount_prev_year


@dataclass
class CategoryData:
    df: pd.DataFrame  # columns: category, amount, share, amount_prev_year, yoy_ratio


@dataclass
class StoreData:
    df: pd.DataFrame  # columns: store_name, region, channel, amount, target_amount, achievement_ratio
    ec_share: float | None
    ec_share_prev_year: float | None


@dataclass
class ProductData:
    top10: pd.DataFrame  # columns: product_name, category, amount, quantity
    worst5: pd.DataFrame  # columns: product_name, category, amount, amount_prev_year, yoy_ratio


@dataclass
class CustomerData:
    new_amount: float
    existing_amount: float
    new_share: float | None
    by_type: pd.DataFrame  # columns: customer_type, amount, share
    unit_price: float | None
    customer_count: int


@dataclass
class ReportData:
    month: date
    region: str | None
    generated_at: datetime
    with_insights: bool = True
    summary: SummaryData | None = None
    trend: TrendData | None = None
    category: CategoryData | None = None
    store: StoreData | None = None
    product: ProductData | None = None
    customer: CustomerData | None = None


def build_summary(engine: Engine, month: date, region: str | None) -> SummaryData:
    months = [month, prev_month(month), prev_year_month(month)]
    company = queries.fetch_company_monthly(engine, months, region)
    store = queries.fetch_store_monthly(engine, [month], region)

    cur = _row(company, month)
    prev = _row(company, prev_month(month))
    prev_y = _row(company, prev_year_month(month))

    amount = int(cur["amount"]) if cur is not None else 0
    gross_profit = int(cur["gross_profit"]) if cur is not None else 0
    gross_margin = safe_div(gross_profit, amount)

    prev_margin = None
    mom_ratio = None
    if prev is not None:
        prev_margin = safe_div(prev["gross_profit"], prev["amount"])
        r = safe_div(amount, prev["amount"])
        mom_ratio = None if r is None else r - 1

    yoy_ratio = None
    if prev_y is not None:
        r = safe_div(amount, prev_y["amount"])
        yoy_ratio = None if r is None else r - 1

    target_amount = int(store["target_amount"].sum()) if not store.empty else None
    achievement_ratio = safe_div(amount, target_amount)

    return SummaryData(
        amount=amount,
        gross_profit=gross_profit,
        gross_margin=gross_margin,
        prev_month_gross_margin=prev_margin,
        mom_ratio=mom_ratio,
        yoy_ratio=yoy_ratio,
        target_amount=target_amount,
        achievement_ratio=achievement_ratio,
    )


def build_trend(engine: Engine, month: date, region: str | None) -> TrendData:
    months_recent = [month_add(month, -i) for i in range(11, -1, -1)]
    months_prev_year = [month_add(m, -12) for m in months_recent]
    all_months = sorted(set(months_recent) | set(months_prev_year))

    company = queries.fetch_company_monthly(engine, all_months, region)
    amounts = company.set_index("month")["amount"]

    df = pd.DataFrame(
        {
            "month": months_recent,
            "amount": [amounts.get(m) for m in months_recent],
            "amount_prev_year": [amounts.get(month_add(m, -12)) for m in months_recent],
        }
    )
    return TrendData(df=df)


def build_category(engine: Engine, month: date, region: str | None) -> CategoryData:
    months = [month, prev_year_month(month)]
    cat = queries.fetch_category_monthly(engine, months, region)

    cur = cat[cat["month"] == month].set_index("category")["amount"]
    prev_y = cat[cat["month"] == prev_year_month(month)].set_index("category")["amount"]
    categories = sorted(set(cur.index) | set(prev_y.index))
    total = float(cur.sum())

    rows = []
    for c in categories:
        amt = float(cur.get(c, 0) or 0)
        py = prev_y.get(c)
        py = None if py is None or pd.isna(py) else float(py)
        share = safe_div(amt, total)
        r = safe_div(amt, py)
        yoy = None if r is None else r - 1
        rows.append(
            {"category": c, "amount": amt, "share": share, "amount_prev_year": py, "yoy_ratio": yoy}
        )

    df = pd.DataFrame(rows).sort_values("amount", ascending=False).reset_index(drop=True)
    return CategoryData(df=df)


def build_store(engine: Engine, month: date, region: str | None) -> StoreData:
    months = [month, prev_year_month(month)]
    store_df = queries.fetch_store_monthly(engine, months, region)

    cur = store_df[store_df["month"] == month].copy()
    cur["achievement_ratio"] = cur.apply(
        lambda r: safe_div(r["amount"], r["target_amount"]), axis=1
    )
    cur = cur.sort_values("achievement_ratio", ascending=False, na_position="last").reset_index(drop=True)

    total_amount = float(cur["amount"].sum())
    ec_amount = float(cur.loc[cur["channel"] == "EC", "amount"].sum())
    ec_share = safe_div(ec_amount, total_amount)

    prev_y = store_df[store_df["month"] == prev_year_month(month)]
    py_total = float(prev_y["amount"].sum())
    py_ec = float(prev_y.loc[prev_y["channel"] == "EC", "amount"].sum())
    ec_share_prev_year = safe_div(py_ec, py_total)

    return StoreData(df=cur, ec_share=ec_share, ec_share_prev_year=ec_share_prev_year)


def build_product(engine: Engine, month: date, region: str | None) -> ProductData:
    months = [month, prev_year_month(month)]
    prod = queries.fetch_product_monthly(engine, months, region)

    cur = prod[prod["month"] == month].sort_values("amount", ascending=False).head(10).reset_index(drop=True)

    py = prod[prod["month"] == prev_year_month(month)][["product_id", "amount"]].rename(
        columns={"amount": "amount_prev_year"}
    )
    merged = prod[prod["month"] == month].merge(py, on="product_id", how="inner")
    merged["yoy_ratio"] = merged.apply(
        lambda r: (safe_div(r["amount"], r["amount_prev_year"]) - 1)
        if safe_div(r["amount"], r["amount_prev_year"]) is not None
        else None,
        axis=1,
    )
    worst5 = merged.dropna(subset=["yoy_ratio"]).sort_values("yoy_ratio").head(5).reset_index(drop=True)

    return ProductData(top10=cur, worst5=worst5)


def build_customer(engine: Engine, month: date, region: str | None) -> CustomerData:
    cust = queries.fetch_customer_monthly(engine, [month], region)

    new_amount = float(cust.loc[cust["is_new"], "amount"].sum())
    existing_amount = float(cust.loc[~cust["is_new"], "amount"].sum())
    total = new_amount + existing_amount
    new_share = safe_div(new_amount, total)

    by_type = cust.groupby("customer_type", as_index=False)["amount"].sum()
    by_type["share"] = by_type["amount"].apply(lambda a: safe_div(a, total))

    customer_count = int(cust["customer_id"].nunique())
    unit_price = safe_div(total, customer_count)

    return CustomerData(
        new_amount=new_amount,
        existing_amount=existing_amount,
        new_share=new_share,
        by_type=by_type,
        unit_price=unit_price,
        customer_count=customer_count,
    )


_SECTION_BUILDERS = {
    "summary": build_summary,
    "trend": build_trend,
    "category": build_category,
    "store": build_store,
    "product": build_product,
    "customer": build_customer,
}


def build_report_data(
    engine: Engine,
    month: date,
    region: str | None,
    sections: set[str],
    *,
    with_insights: bool = True,
) -> ReportData:
    data = ReportData(
        month=month, region=region, generated_at=datetime.now(), with_insights=with_insights
    )
    for name in sections:
        setattr(data, name, _SECTION_BUILDERS[name](engine, month, region))
    return data
