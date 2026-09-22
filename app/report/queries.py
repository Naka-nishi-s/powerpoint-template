"""データ取得（DataFrameを返す）。SQLはプレースホルダで値を渡し、文字列連結はしない。

集計ビュー（sales.v_monthly_*）は拠点で絞り込めないため、拠点フィルタに対応する
必要がある取得関数はビューと同じ粒度のSQLをここで組み立てて実行する。
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import Engine, bindparam, text


def _months_query(sql: str):
    return text(sql).bindparams(bindparam("months", expanding=True))


def fetch_available_months(engine: Engine) -> list[date]:
    sql = text("SELECT DISTINCT month FROM sales.v_monthly_sales ORDER BY 1")
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return list(df["month"])


def fetch_regions(engine: Engine) -> list[str]:
    sql = text("SELECT DISTINCT region FROM sales.stores ORDER BY 1")
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return list(df["region"])


def fetch_company_monthly(engine: Engine, months: list[date], region: str | None) -> pd.DataFrame:
    sql = _months_query(
        """
        SELECT
            date_trunc('month', s.sale_date)::date AS month,
            SUM(s.amount)                             AS amount,
            SUM(s.amount - s.quantity * p.cost_price)  AS gross_profit,
            SUM(s.quantity)                            AS quantity,
            COUNT(*)                                   AS order_count
        FROM sales.sales s
        JOIN sales.products p ON p.product_id = s.product_id
        JOIN sales.stores st ON st.store_id = s.store_id
        WHERE date_trunc('month', s.sale_date)::date IN :months
          AND (CAST(:region AS text) IS NULL OR st.region = :region)
        GROUP BY 1
        ORDER BY 1
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"months": months, "region": region})


def fetch_category_monthly(engine: Engine, months: list[date], region: str | None) -> pd.DataFrame:
    sql = _months_query(
        """
        SELECT
            date_trunc('month', s.sale_date)::date    AS month,
            p.category                                 AS category,
            SUM(s.amount)                              AS amount,
            SUM(s.amount - s.quantity * p.cost_price)   AS gross_profit
        FROM sales.sales s
        JOIN sales.products p ON p.product_id = s.product_id
        JOIN sales.stores st ON st.store_id = s.store_id
        WHERE date_trunc('month', s.sale_date)::date IN :months
          AND (CAST(:region AS text) IS NULL OR st.region = :region)
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"months": months, "region": region})


def fetch_store_monthly(engine: Engine, months: list[date], region: str | None) -> pd.DataFrame:
    sql = _months_query(
        """
        SELECT
            t.year_month                     AS month,
            st.store_id                      AS store_id,
            st.store_name                    AS store_name,
            st.region                        AS region,
            st.channel                       AS channel,
            COALESCE(SUM(s.amount), 0)       AS amount,
            t.target_amount                  AS target_amount
        FROM sales.targets t
        JOIN sales.stores st ON st.store_id = t.store_id
        LEFT JOIN sales.sales s
            ON s.store_id = t.store_id
           AND date_trunc('month', s.sale_date)::date = t.year_month
        WHERE t.year_month IN :months
          AND (CAST(:region AS text) IS NULL OR st.region = :region)
        GROUP BY 1, 2, 3, 4, 5, t.target_amount
        ORDER BY 1, 2
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"months": months, "region": region})


def fetch_product_monthly(engine: Engine, months: list[date], region: str | None) -> pd.DataFrame:
    sql = _months_query(
        """
        SELECT
            date_trunc('month', s.sale_date)::date AS month,
            p.product_id                            AS product_id,
            p.product_name                          AS product_name,
            p.category                              AS category,
            SUM(s.amount)                           AS amount,
            SUM(s.quantity)                         AS quantity
        FROM sales.sales s
        JOIN sales.products p ON p.product_id = s.product_id
        JOIN sales.stores st ON st.store_id = s.store_id
        WHERE date_trunc('month', s.sale_date)::date IN :months
          AND (CAST(:region AS text) IS NULL OR st.region = :region)
        GROUP BY 1, 2, 3, 4
        ORDER BY 1, 5 DESC
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"months": months, "region": region})


def fetch_customer_monthly(engine: Engine, months: list[date], region: str | None) -> pd.DataFrame:
    sql = _months_query(
        """
        SELECT
            date_trunc('month', s.sale_date)::date AS month,
            c.customer_id                           AS customer_id,
            c.customer_type                         AS customer_type,
            (date_trunc('month', c.first_purchase_date)::date
                = date_trunc('month', s.sale_date)::date) AS is_new,
            SUM(s.amount)                           AS amount
        FROM sales.sales s
        JOIN sales.customers c ON c.customer_id = s.customer_id
        JOIN sales.stores st ON st.store_id = s.store_id
        WHERE date_trunc('month', s.sale_date)::date IN :months
          AND (CAST(:region AS text) IS NULL OR st.region = :region)
        GROUP BY 1, 2, 3, 4
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"months": months, "region": region})
