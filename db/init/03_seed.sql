-- サンプルデータ生成
-- generate_series と setseed() で乱数を固定し、毎回同じデータになるようにする

SET search_path TO sales;

SELECT setseed(0.4321);

-- ---------- products（商品50件） ----------
INSERT INTO products (product_name, category, sub_category, list_price, cost_price)
SELECT
    '商品' || lpad(i::text, 3, '0') AS product_name,
    (ARRAY['食品・飲料', '日用雑貨', '家電', 'アパレル', 'インテリア'])[((i - 1) % 5) + 1] AS category,
    (ARRAY['定番', '季節', '新商品', '業務用', 'ギフト'])[1 + floor(random() * 5)::int] AS sub_category,
    lp.list_price,
    (lp.list_price * (0.5 + random() * 0.2))::int AS cost_price
FROM generate_series(1, 50) AS i
CROSS JOIN LATERAL (SELECT (800 + floor(random() * 29200))::int AS list_price) lp;

-- ---------- customers（顧客500件） ----------
-- first_purchase_date はいったん広い範囲で仮置きし、売上生成後に
-- レポート対象期間内の顧客は実際の初回売上日で上書きする
INSERT INTO customers (customer_name, customer_type, region, first_purchase_date)
SELECT
    '顧客' || lpad(i::text, 4, '0'),
    CASE WHEN random() < 0.25 THEN '法人' ELSE '個人' END,
    (ARRAY['北海道', '東北', '関東', '中部', '関西', '九州'])[1 + floor(random() * 6)::int],
    (DATE '2022-01-01' + floor(random() * 1704)::int)::date
FROM generate_series(1, 500) AS i;

-- ---------- stores（店舗10件、うちEC 1件） ----------
INSERT INTO stores (store_name, region, channel) VALUES
    ('札幌店',           '北海道', '店舗'),
    ('仙台店',           '東北',   '店舗'),
    ('東京本店',         '関東',   '店舗'),
    ('横浜店',           '関東',   '店舗'),
    ('名古屋店',         '中部',   '店舗'),
    ('大阪店',           '関西',   '店舗'),
    ('京都店',           '関西',   '店舗'),
    ('福岡店',           '九州',   '店舗'),
    ('那覇店',           '九州',   '店舗'),
    ('オンラインストア', '関東',   'EC');

-- ---------- sales（24か月分、約10万件） ----------
-- 傾向：12月・3月は繁忙期、2月・8月は閑散期。
--       ECは月を追うごとに構成比が上昇。アパレルは構成比が緩やかに低下。
DO $$
DECLARE
    n_stores   int;
    n_products int;
    store_ids        int[];
    store_is_ec      boolean[];
    store_base_w     numeric[];
    product_ids      int[];
    product_category text[];
    product_list     int[];

    v_month_idx     int;
    v_month         date;
    v_month_num     int;
    v_days_in_month int;
    v_season_mult   numeric;
    v_txn_count     int;

    store_cum   numeric[];
    store_total numeric;
    prod_cum    numeric[];
    prod_total  numeric;

    v_cat_decline_mult numeric;

    i int;
    j int;
    pick numeric;
    chosen_store    int;
    chosen_product  int;
    prod_idx        int;
    chosen_customer int;
    v_qty        int;
    v_unit_price int;
    v_discount   int;
    v_amount     int;
BEGIN
    SELECT array_agg(store_id ORDER BY store_id),
           array_agg(channel = 'EC' ORDER BY store_id),
           array_agg(0.7 + random() * 0.6 ORDER BY store_id)
    INTO store_ids, store_is_ec, store_base_w
    FROM stores;
    n_stores := array_length(store_ids, 1);

    SELECT array_agg(product_id ORDER BY product_id),
           array_agg(category ORDER BY product_id),
           array_agg(list_price ORDER BY product_id)
    INTO product_ids, product_category, product_list
    FROM products;
    n_products := array_length(product_ids, 1);

    FOR v_month_idx IN 0..23 LOOP
        v_month := (DATE '2024-09-01' + (v_month_idx || ' months')::interval)::date;
        v_month_num := EXTRACT(MONTH FROM v_month)::int;
        v_days_in_month := EXTRACT(DAY FROM (v_month + INTERVAL '1 month - 1 day'))::int;

        v_season_mult := CASE
            WHEN v_month_num IN (12, 3) THEN 1.4
            WHEN v_month_num IN (2, 8) THEN 0.7
            ELSE 1.0
        END;
        v_txn_count := round(4200 * v_season_mult * (0.95 + random() * 0.1))::int;

        -- 店舗の重み（ECは月を追うごとに構成比が上昇）
        store_cum := ARRAY[]::numeric[];
        store_total := 0;
        FOR j IN 1..n_stores LOOP
            store_total := store_total + (
                CASE WHEN store_is_ec[j]
                     THEN store_base_w[j] * (1.0 + v_month_idx * 0.06)
                     ELSE store_base_w[j]
                END
            );
            store_cum := array_append(store_cum, store_total);
        END LOOP;

        -- 商品の重み（アパレルは月を追うごとに構成比が低下）
        v_cat_decline_mult := GREATEST(0.5, 1.3 - v_month_idx * 0.025);
        prod_cum := ARRAY[]::numeric[];
        prod_total := 0;
        FOR j IN 1..n_products LOOP
            prod_total := prod_total + (
                CASE WHEN product_category[j] = 'アパレル'
                     THEN v_cat_decline_mult
                     ELSE 1.0
                END
            );
            prod_cum := array_append(prod_cum, prod_total);
        END LOOP;

        FOR i IN 1..v_txn_count LOOP
            pick := random() * store_total;
            chosen_store := store_ids[n_stores];
            FOR j IN 1..n_stores LOOP
                IF pick <= store_cum[j] THEN
                    chosen_store := store_ids[j];
                    EXIT;
                END IF;
            END LOOP;

            pick := random() * prod_total;
            chosen_product := product_ids[n_products];
            prod_idx := n_products;
            FOR j IN 1..n_products LOOP
                IF pick <= prod_cum[j] THEN
                    chosen_product := product_ids[j];
                    prod_idx := j;
                    EXIT;
                END IF;
            END LOOP;

            chosen_customer := 1 + floor(random() * 500)::int;
            v_qty := 1 + floor(random() * 5)::int;
            v_unit_price := round(product_list[prod_idx] * (0.9 + random() * 0.15))::int;
            v_discount := CASE WHEN random() < 0.2
                THEN round(v_qty * v_unit_price * (0.05 + random() * 0.1))::int
                ELSE 0
            END;
            v_amount := v_qty * v_unit_price - v_discount;

            INSERT INTO sales (sale_date, product_id, customer_id, store_id, quantity, unit_price, discount, amount)
            VALUES (
                v_month + floor(random() * v_days_in_month)::int,
                chosen_product,
                chosen_customer,
                chosen_store,
                v_qty,
                v_unit_price,
                v_discount,
                v_amount
            );
        END LOOP;
    END LOOP;
END $$;

-- レポート対象期間内に仮の初回購入日を持つ顧客は、実際の初回売上日で上書きする
UPDATE customers c
SET first_purchase_date = sub.min_date
FROM (
    SELECT customer_id, MIN(sale_date) AS min_date
    FROM sales
    GROUP BY customer_id
) sub
WHERE c.customer_id = sub.customer_id
  AND c.first_purchase_date >= DATE '2024-09-01';

-- ---------- targets（月次予算） ----------
-- 店舗ごとの実績平均に係数をかけて予算を設定する。
-- 仙台店・名古屋店・那覇店は係数を高めにして予算未達が出やすくする。
INSERT INTO targets (year_month, store_id, target_amount)
SELECT
    m.month,
    st.store_id,
    GREATEST(
        1,
        ROUND(
            avgs.avg_amt
            * CASE WHEN st.store_name IN ('仙台店', '名古屋店', '那覇店') THEN 1.12 ELSE 0.92 END
            * (0.92 + random() * 0.16)
        )
    )::bigint AS target_amount
FROM (SELECT DISTINCT date_trunc('month', sale_date)::date AS month FROM sales) m
CROSS JOIN stores st
JOIN (
    SELECT store_id, AVG(monthly_amt) AS avg_amt
    FROM (
        SELECT store_id, date_trunc('month', sale_date)::date AS month, SUM(amount) AS monthly_amt
        FROM sales
        GROUP BY 1, 2
    ) x
    GROUP BY store_id
) avgs ON avgs.store_id = st.store_id;

ANALYZE sales;
ANALYZE targets;
ANALYZE customers;
ANALYZE products;
ANALYZE stores;
