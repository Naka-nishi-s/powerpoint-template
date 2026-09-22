# 月次売上レポート自動生成ツール

PostgreSQLに蓄積した売上データから、月次売上レポートのたたき台（PowerPoint）を自動生成するツールです。Streamlit画面で対象月・拠点を選ぶだけで、集計とPPTX生成を行います。

## 起動方法

1. `.env.example` をコピーして `.env` を作成し、パスワードなどを設定する

   ```
   cp .env.example .env
   ```

2. Docker Composeでコンテナを起動する

   ```
   docker compose up -d
   ```

3. ブラウザでアクセスする

   - アプリ（Streamlit）: http://localhost:8501
   - pgAdmin（DB管理）: http://localhost:5050

初回起動時は `db/init/` 配下のSQLが実行され、サンプルデータ（24か月分）が投入されます。

## 停止・データ削除

```
docker compose down       # 停止
docker compose down -v    # 停止 + データ（ボリューム）も削除
```
