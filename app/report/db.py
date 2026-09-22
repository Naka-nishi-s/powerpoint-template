"""DB接続。接続情報はこのモジュールだけで扱う。"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine

_engine: Engine | None = None


def _build_url() -> str:
    user = os.environ["REPORT_DB_USER"]
    password = os.environ["REPORT_DB_PASSWORD"]
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    dbname = os.environ["POSTGRES_DB"]
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def get_engine() -> Engine:
    """読み取り専用ロール（report_ro）で接続するEngineを返す。"""
    global _engine
    if _engine is None:
        _engine = create_engine(_build_url(), pool_pre_ping=True)
    return _engine
