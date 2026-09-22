"""CLI実行用の入口（テスト・将来の定期実行用）。画面と同じ関数を呼ぶ。

使い方:
    python cli.py --month 2026-08 --slide summary       # パターンA
    python cli.py --month 2026-08                       # パターンB（全スライド）
    python cli.py --month 2026-08 --slides trend,store   # パターンB（選択）
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from report.generate import build_filename, generate_report, generate_slide
from report.slides import SLIDES


def _parse_month(value: str) -> date:
    return datetime.strptime(value, "%Y-%m").date().replace(day=1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="月次売上レポートを生成する")
    parser.add_argument("--month", required=True, type=_parse_month, help="対象月（YYYY-MM）")
    parser.add_argument("--region", default=None, help="拠点で絞り込む場合の地域名")
    parser.add_argument("--slide", default=None, choices=sorted(SLIDES), help="パターンA：1枚だけ出力するスライドID")
    parser.add_argument("--slides", default=None, help="パターンB：出力するスライドIDをカンマ区切りで指定（省略時は全スライド）")
    parser.add_argument("--no-insights", action="store_true", help="所見スライドの自動生成テキストを含めない")
    parser.add_argument("--out", default=".", help="出力先ディレクトリ（既定はカレントディレクトリ）")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.slide:
        content = generate_slide(args.month, args.slide, args.region)
        filename = build_filename(args.month, slide_id=args.slide, region=args.region)
    else:
        slide_list = args.slides.split(",") if args.slides else None
        content = generate_report(
            args.month, args.region, slide_list, with_insights=not args.no_insights
        )
        filename = build_filename(args.month, region=args.region)

    out_path = out_dir / filename
    out_path.write_bytes(content)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
