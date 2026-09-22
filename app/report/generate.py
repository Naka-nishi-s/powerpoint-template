"""generate_slide() / generate_report() -> bytes

両関数とも同じスライドビルダー（slides.SLIDES）を呼ぶため、1枚ずつ出しても
一括で出しても、同じスライドの中身は一致する。
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from pptx import Presentation
from sqlalchemy import Engine

from . import metrics
from .db import get_engine
from .slides import SLIDE_DATA_SECTIONS, SLIDE_ORDER, SLIDES

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "base.pptx"


def _new_presentation() -> Presentation:
    return Presentation(str(TEMPLATE_PATH))


def _save_bytes(prs: Presentation) -> bytes:
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def build_filename(month: date, *, slide_id: str | None = None, region: str | None = None) -> str:
    """6.1 / 6.4：ファイル名規則。"""
    name = f"月次売上レポート_{month:%Y-%m}"
    if slide_id is not None:
        name += f"_{slide_id}"
    if region:
        name += f"_{region}"
    return name + ".pptx"


def generate_slide(month: date, slide_id: str, region: str | None = None, *, engine: Engine | None = None) -> bytes:
    """パターンA：指定した1枚だけのpptxを返す"""
    if slide_id not in SLIDES:
        raise ValueError(f"unknown slide_id: {slide_id}")

    engine = engine or get_engine()
    sections = SLIDE_DATA_SECTIONS[slide_id]
    data = metrics.build_report_data(engine, month, region, sections)

    prs = _new_presentation()
    SLIDES[slide_id](prs, data)
    return _save_bytes(prs)


def generate_report(
    month: date,
    region: str | None = None,
    slides: list[str] | None = None,
    with_insights: bool = True,
    *,
    engine: Engine | None = None,
) -> bytes:
    """パターンB：選択したスライドを順番にまとめたpptxを返す（表紙・サマリーは常に含める）"""
    selected = set(slides) if slides is not None else set(SLIDE_ORDER)
    selected |= {"cover", "summary"}
    ordered = [slide_id for slide_id in SLIDE_ORDER if slide_id in selected]

    engine = engine or get_engine()
    needed_sections: set[str] = set()
    for slide_id in ordered:
        needed_sections |= SLIDE_DATA_SECTIONS[slide_id]

    data = metrics.build_report_data(
        engine, month, region, needed_sections, with_insights=with_insights
    )

    prs = _new_presentation()
    for slide_id in ordered:
        SLIDES[slide_id](prs, data)
    return _save_bytes(prs)
