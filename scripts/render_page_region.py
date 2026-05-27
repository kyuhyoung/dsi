"""PDF 특정 페이지의 일부 영역을 고해상도로 렌더. 시각 검증 확대용.

용법: python scripts/render_page_region.py <pdf> <page1based> <out.png> <left> <top> <right> <bottom> [dpi]
좌표는 0~1 비율, dpi 기본 200.
"""
import sys
import fitz

pdf, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
l, t, r, b = [float(x) for x in sys.argv[4:8]]
dpi = int(sys.argv[8]) if len(sys.argv) > 8 else 200

doc = fitz.open(pdf)
pg = doc[page - 1]
rect = pg.rect
clip = fitz.Rect(rect.x0 + rect.width * l, rect.y0 + rect.height * t,
                 rect.x0 + rect.width * r, rect.y0 + rect.height * b)
pix = pg.get_pixmap(dpi=dpi, clip=clip)
pix.save(out)
print("saved {} ({}x{}px)".format(out, pix.width, pix.height))
doc.close()
