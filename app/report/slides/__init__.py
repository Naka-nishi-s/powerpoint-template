"""スライドビルダーのレジストリ。

各ビルダーの共通シグネチャ：受け取ったPresentationに1枚追加する
def build_xxx(prs: Presentation, data: ReportData) -> None
"""

from __future__ import annotations

from .category import build_category
from .cover import build_cover
from .customer import build_customer
from .insights import build_insights
from .product import build_product
from .store import build_store
from .summary import build_summary
from .trend import build_trend

SLIDES = {
    "cover": build_cover,  # 1 表紙
    "summary": build_summary,  # 2 サマリー
    "trend": build_trend,  # 3 売上推移
    "category": build_category,  # 4 カテゴリ別売上
    "store": build_store,  # 5 地域・店舗別実績
    "product": build_product,  # 6 商品ランキング
    "customer": build_customer,  # 7 顧客分析
    "insights": build_insights,  # 8 所見・課題
}

# 各スライドがReportDataのどのセクションを必要とするか（generate.pyが実行するクエリを絞るのに使う）
SLIDE_DATA_SECTIONS: dict[str, set[str]] = {
    "cover": set(),
    "summary": {"summary"},
    "trend": {"trend"},
    "category": {"category"},
    "store": {"store"},
    "product": {"product"},
    "customer": {"customer"},
    "insights": {"summary", "category", "store"},
}

# スライド表示順（表紙とサマリーは常に含める。6.2の並び）
SLIDE_ORDER = ["cover", "summary", "trend", "category", "store", "product", "customer", "insights"]
