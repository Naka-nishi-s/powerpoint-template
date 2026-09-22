#!/bin/sh
# 読み取り専用ロール（report_ro）を作成する。
# パスワードを環境変数から埋め込むため、SQLファイルではなくshで実行する。
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${REPORT_DB_USER}') THEN
            CREATE ROLE "${REPORT_DB_USER}" LOGIN PASSWORD '${REPORT_DB_PASSWORD}';
        END IF;
    END
    \$\$;

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${REPORT_DB_USER}";
    GRANT USAGE ON SCHEMA sales TO "${REPORT_DB_USER}";
    GRANT SELECT ON ALL TABLES IN SCHEMA sales TO "${REPORT_DB_USER}";
    ALTER DEFAULT PRIVILEGES IN SCHEMA sales GRANT SELECT ON TABLES TO "${REPORT_DB_USER}";
EOSQL
