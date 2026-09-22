"""templates/base.pptx（16:9のスライドマスター雛形）を生成する。
一度だけ実行して成果物をリポジトリにコミットする想定。
"""

from pptx import Presentation
from pptx.util import Inches

OUTPUT = "app/templates/base.pptx"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
prs.save(OUTPUT)
print(f"wrote {OUTPUT}")
