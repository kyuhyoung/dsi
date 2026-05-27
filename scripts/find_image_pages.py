"""PDF에서 래스터 이미지가 박힌 페이지를 찾는다. 시각 검증 보조용.

용법: python scripts/find_image_pages.py <input.pdf>
"""
import sys
import fitz

doc = fitz.open(sys.argv[1])
for i in range(doc.page_count):
    imgs = doc[i].get_images()
    if imgs:
        sizes = []
        for im in imgs:
            xref = im[0]
            d = doc.extract_image(xref)
            sizes.append("{}x{}".format(d.get("width"), d.get("height")))
        print("page {}: {} image(s) {}".format(i + 1, len(imgs), ", ".join(sizes)))
doc.close()
