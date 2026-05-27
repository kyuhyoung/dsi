"""PDF 전체 텍스트 추출 (PyMuPDF). RFP 분석·검색용.

용법: python scripts/pdf_to_text.py <input.pdf> [<out.txt>]
out 생략 시 stdout.
"""
import sys
import fitz

doc = fitz.open(sys.argv[1])
parts = []
for i in range(doc.page_count):
    parts.append("\n===== page {} =====\n".format(i + 1))
    parts.append(doc[i].get_text())
doc.close()
text = "".join(parts)

if len(sys.argv) > 2:
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(text)
    print("saved {} ({} chars)".format(sys.argv[2], len(text)))
else:
    sys.stdout.write(text)
