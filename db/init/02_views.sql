-- 集計ビュー（すべて sales スキーマ）
-- 月は date_trunc('month', sale_date)::date で表す

SET search_path TO sales;

-- v_monthly_sales: 月単位の全社サマリー
CREATE VIEW v_monthly_sales AS
SELECT
    date_trunc('month', s.sale_date)::date AS month,
    SUM(s.amount)                          AS amount,
    SUM(s.amount - s.quantity * p.cost_price) AS gross_profit,
    SUM(s.quantity)                        AS quantity,
    COUNT(*)                               AS order_count
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY 1;

-- v_monthly_category: 月 × カテゴリ
CREATE VIEW v_monthly_category AS
SELECT
    date_trunc('month', s.sale_date)::date AS month,
    p.category,
    SUM(s.amount)                          AS amount,
    SUM(s.amount - s.quantity * p.cost_price) AS gross_profit
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY 1, 2;

-- v_monthly_store: 月 × 店舗（予算はtargetsに存在する店舗・月のみ）
CREATE VIEW v_monthly_store AS
WITH monthly_store_sales AS (
    SELECT
        date_trunc('month', sale_date)::date AS month,
        store_id,
        SUM(amount) AS amount
    FROM sales
    GROUP BY 1, 2
)
SELECT
    t.year_month           AS month,
    st.store_id,
    st.store_name,
    st.region,
    st.channel,
    COALESCE(mss.amount, 0) AS amount,
    t.target_amount
FROM targets t
JOIN stores st ON st.store_id = t.store_id
LEFT JOIN monthly_store_sales mss
    ON mss.store_id = t.store_id AND mss.month = t.year_month;

-- v_monthly_product: 月 × 商品
CREATE VIEW v_monthly_product AS
SELECT
    date_trunc('month', s.sale_date)::date AS month,
    p.product_id,
    p.product_name,
    p.category,
    SUM(s.amount)   AS amount,
    SUM(s.quantity) AS quantity
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY 1, 2, 3, 4;

-- v_monthly_customer: 月 × 顧客
CREATE VIEW v_monthly_customer AS
SELECT
    date_trunc('month', s.sale_date)::date AS month,
    c.customer_id,
    c.customer_type,
    (date_trunc('month', c.first_purchase_date)::date
        = date_trunc('month', s.sale_date)::date) AS is_new,
    SUM(s.amount) AS amount
FROM sales s
JOIN customers c ON c.customer_id = s.customer_id
GROUP BY 1, 2, 3, 4;
