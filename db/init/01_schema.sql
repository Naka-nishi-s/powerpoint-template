-- テーブル定義（スキーマ: sales）

CREATE SCHEMA IF NOT EXISTS sales;

SET search_path TO sales;

-- 4.1 products（商品マスタ）
CREATE TABLE products (
    product_id   serial PRIMARY KEY,
    product_name varchar(100) NOT NULL,
    category     varchar(50)  NOT NULL,
    sub_category varchar(50),
    list_price   integer NOT NULL,
    cost_price   integer NOT NULL
);

-- 4.2 customers（顧客マスタ）
CREATE TABLE customers (
    customer_id         serial PRIMARY KEY,
    customer_name        varchar(100) NOT NULL,
    customer_type         varchar(10) NOT NULL CHECK (customer_type IN ('法人', '個人')),
    region                varchar(20) NOT NULL,
    first_purchase_date   date
);

-- 4.3 stores（店舗・拠点マスタ）
CREATE TABLE stores (
    store_id   serial PRIMARY KEY,
    store_name varchar(100) NOT NULL,
    region     varchar(20) NOT NULL,
    channel    varchar(10) NOT NULL CHECK (channel IN ('店舗', 'EC'))
);

-- 4.4 sales（売上明細）
CREATE TABLE sales (
    sale_id     bigserial PRIMARY KEY,
    sale_date   date NOT NULL,
    product_id  integer NOT NULL REFERENCES products (product_id),
    customer_id integer NOT NULL REFERENCES customers (customer_id),
    store_id    integer NOT NULL REFERENCES stores (store_id),
    quantity    integer NOT NULL CHECK (quantity > 0),
    unit_price  integer NOT NULL,
    discount    integer NOT NULL DEFAULT 0,
    amount      integer NOT NULL
);

CREATE INDEX idx_sales_sale_date ON sales (sale_date);
CREATE INDEX idx_sales_store_date ON sales (store_id, sale_date);
CREATE INDEX idx_sales_product_date ON sales (product_id, sale_date);

-- 4.5 targets（月次予算）
CREATE TABLE targets (
    year_month    date NOT NULL,
    store_id      integer NOT NULL REFERENCES stores (store_id),
    target_amount bigint NOT NULL,
    PRIMARY KEY (year_month, store_id)
);
