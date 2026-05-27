"""PDF → 페이지별 PNG 렌더 (PyMuPDF). 시각 검증용.

용법:
    python scripts/pdf_to_png.py <input.pdf> <out_dir> [dpi]
"""
import sys
import os
import fitz


def render(pdf_path: str, out_dir: str, dpi: int = 110):
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    paths = []
    for i in range(doc.page_count):
        pix = doc[i].get_pixmap(dpi=dpi)
        p = os.path.join(out_dir, "page_{:02d}.png".format(i + 1))
        pix.save(p)
        paths.append(p)
    doc.close()
    print("pages: {}, out: {}".format(len(paths), out_dir))
    return paths


if __name__ == "__main__":
    pdf = sys.argv[1]
    out = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 110
    render(pdf, out, dpi)
