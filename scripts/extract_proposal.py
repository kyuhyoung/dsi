#!/usr/bin/env python3
"""제안서 (또는 RFP) 파일에서 평문 텍스트 추출.

지원 포맷:
    .md    → 그대로 (마크다운 보존)
    .txt   → 그대로
    .docx  → python-docx로 본문 단락·표 추출
    .hwp   → hwp5txt CLI (pyhwp 패키지 제공)
    .hwpx  → zipfile + xml.etree로 직접 파싱
    .pdf   → pdftotext 또는 pdfplumber

사용:
    python3 scripts/extract_proposal.py <파일경로> [<출력경로>]

출력경로 생략 시 stdout으로 출력.
"""
import io
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_md_or_txt(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def extract_docx(path):
    """python-docx로 단락 + 표 텍스트 추출. 헤딩은 #/##로 표시."""
    from docx import Document
    doc = Document(str(path))
    out = []
    for block in _iter_block_items(doc):
        if block.__class__.__name__ == "Paragraph":
            style = (block.style.name or "").lower() if block.style else ""
            text = block.text.strip()
            if not text:
                continue
            if "heading 1" in style:
                out.append(f"# {text}")
            elif "heading 2" in style:
                out.append(f"## {text}")
            elif "heading 3" in style:
                out.append(f"### {text}")
            else:
                out.append(text)
        elif block.__class__.__name__ == "Table":
            for row in block.rows:
                cells = [c.text.strip() for c in row.cells]
                out.append(" | ".join(cells))
    return "\n\n".join(out)


def _iter_block_items(parent):
    """python-docx Document의 단락·표를 문서 순서대로 yield."""
    from docx.document import Document as DocClass
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    if isinstance(parent, DocClass):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._element
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _html_to_text(html_str):
    """HTML → 평문. 표 구조는 행/셀 분리 보존, 단락은 줄바꿈."""
    import re as _re
    h = html_str
    # script·style 블록 통째 제거 (CSS·JS 본문 오염 방지)
    h = _re.sub(r"<style[^>]*>.*?</style>", "", h, flags=_re.I | _re.S)
    h = _re.sub(r"<script[^>]*>.*?</script>", "", h, flags=_re.I | _re.S)
    # head 블록 통째 제거
    h = _re.sub(r"<head[^>]*>.*?</head>", "", h, flags=_re.I | _re.S)
    # 표 행 종료 → 줄바꿈
    h = _re.sub(r"</tr\s*>", "\n", h, flags=_re.I)
    # 표 셀 사이 → " | "
    h = _re.sub(r"</t[dh]\s*>\s*<t[dh][^>]*>", " | ", h, flags=_re.I)
    h = _re.sub(r"<t[dh][^>]*>", "", h, flags=_re.I)
    h = _re.sub(r"</t[dh]\s*>", "", h, flags=_re.I)
    # 단락 종료 + br → 줄바꿈
    h = _re.sub(r"</p\s*>", "\n", h, flags=_re.I)
    h = _re.sub(r"<br\s*/?>", "\n", h, flags=_re.I)
    # 헤딩
    h = _re.sub(r"</h[1-6]\s*>", "\n\n", h, flags=_re.I)
    # 나머지 태그 제거
    h = _re.sub(r"<[^>]+>", "", h)
    # HTML entity 디코딩
    h = h.replace("&#13;", "\n").replace("&nbsp;", " ")
    h = h.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    h = _re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), h)
    h = _re.sub(r"&[a-zA-Z]+;", " ", h)
    # 공백 정리
    h = _re.sub(r"[ \t]+", " ", h)
    h = _re.sub(r"\n[ \t]+", "\n", h)
    h = _re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


def extract_hwp(path):
    """hwp5html 사용 — 표 내용 보존 + 이미지 동시 dump.

    HWP 파일과 같은 폴더에 <basename>.assets/ 폴더 생성:
    - 본문 텍스트는 함수 리턴값
    - 이미지는 BIN*.png/BIN*.bmp 등으로 dump
    """
    import tempfile as _tempfile
    if not shutil.which("hwp5html"):
        # 폴백: 구버전 hwp5txt 시도
        if shutil.which("hwp5txt"):
            proc = subprocess.run(
                ["hwp5txt", str(path)],
                capture_output=True, text=True, timeout=120
            )
            if proc.returncode == 0:
                return proc.stdout
        raise RuntimeError(
            "hwp5html 명령 없음. 설치: pip3 install --user pyhwp"
        )

    src = Path(path).resolve()
    assets_dir = src.parent / f"{src.stem}.assets"

    with _tempfile.TemporaryDirectory(prefix="dsi_hwp_") as tmp:
        proc = subprocess.run(
            ["hwp5html", str(src)],
            cwd=tmp,
            capture_output=True, text=True, timeout=300
        )
        if proc.returncode != 0:
            raise RuntimeError(f"hwp5html 실패: {proc.stderr}")
        out_dir = Path(tmp) / src.stem
        html_path = out_dir / "index.xhtml"
        if not html_path.exists():
            raise RuntimeError(f"hwp5html 출력 누락: {html_path}")
        # 이미지 dump (같은 위치에 갱신)
        bindata = out_dir / "bindata"
        if bindata.exists():
            if assets_dir.exists():
                shutil.rmtree(assets_dir)
            shutil.copytree(bindata, assets_dir)
            n_imgs = sum(1 for _ in assets_dir.iterdir())
            print(f"  이미지 {n_imgs}장 dump: {assets_dir}", file=sys.stderr)
        return _html_to_text(html_path.read_text(encoding="utf-8"))


_HWPX_TEXT_TAG = "{http://www.hancom.co.kr/hwpml/2011/paragraph}t"


def extract_hwpx(path):
    """.hwpx (zip + XML) 직접 파싱. Contents/section*.xml 의 <hp:t> 텍스트 노드 추출."""
    out = []
    with zipfile.ZipFile(str(path)) as zf:
        section_names = sorted(
            n for n in zf.namelist()
            if n.startswith("Contents/section") and n.endswith(".xml")
        )
        for name in section_names:
            try:
                xml_bytes = zf.read(name)
                root = ET.fromstring(xml_bytes)
                # 텍스트 노드 모두 수집
                paragraph_texts = []
                # 단락 단위로 묶기 위해 hp:p 단락 단위로 순회
                for p in root.iter():
                    if not p.tag.endswith("}p"):
                        continue
                    runs = [t.text for t in p.iter(_HWPX_TEXT_TAG) if t.text]
                    line = "".join(runs).strip()
                    if line:
                        paragraph_texts.append(line)
                if paragraph_texts:
                    out.append("\n".join(paragraph_texts))
            except ET.ParseError as e:
                print(f"warning: {name} 파싱 실패: {e}", file=sys.stderr)
    if not out:
        raise RuntimeError(f"{path}에서 텍스트 추출 실패 (빈 hwpx?)")
    return "\n\n".join(out)


def extract_pdf(path):
    """pdftotext 또는 pdfplumber. 둘 다 없으면 오류."""
    if shutil.which("pdftotext"):
        proc = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True, text=True, timeout=120
        )
        if proc.returncode == 0:
            return proc.stdout
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return "\n\n".join(p.extract_text() or "" for p in pdf.pages)
    except ImportError:
        pass
    raise RuntimeError(
        "PDF 추출 도구 없음. 설치: sudo apt install poppler-utils  "
        "또는 pip3 install --user pdfplumber"
    )


_EXTRACTORS = {
    ".md":   extract_md_or_txt,
    ".txt":  extract_md_or_txt,
    ".docx": extract_docx,
    ".hwp":  extract_hwp,
    ".hwpx": extract_hwpx,
    ".pdf":  extract_pdf,
}


def extract(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"파일 없음: {p}")
    ext = p.suffix.lower()
    if ext not in _EXTRACTORS:
        raise ValueError(
            f"지원하지 않는 포맷: {ext} (지원: {', '.join(_EXTRACTORS.keys())})"
        )
    return _EXTRACTORS[ext](p)


def main():
    if len(sys.argv) < 2:
        print(
            "사용: python3 scripts/extract_proposal.py <파일경로> [<출력경로>]\n"
            "지원: .md .txt .docx .hwp .hwpx .pdf",
            file=sys.stderr,
        )
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) >= 3 else None
    try:
        text = extract(src)
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(2)
    if dst:
        Path(dst).write_text(text, encoding="utf-8")
        print(f"saved: {dst} ({len(text)} chars)", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
