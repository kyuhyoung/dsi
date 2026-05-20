#!/usr/bin/env python3
"""템플릿 .pptx의 각 슬라이드를 PNG 썸네일로 렌더.

용도:
- analyze_template.py 가 키워드 점수 기반으로 매핑한 결과를
  Claude Code 세션에서 사람·LLM이 visual로 검증
- templates/<name>.thumbnails/slide_NN.png 생성

의존성:
- LibreOffice (soffice / Windows /mnt/c/Program Files/...)
- pdftoppm (poppler-utils)

사용:
    python3 scripts/render_thumbnails.py <template.pptx> [<out_dir>]
"""
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_soffice():
    for cmd in ("soffice", "libreoffice"):
        if shutil.which(cmd):
            return cmd
    for p in (
        "/mnt/c/Program Files/LibreOffice/program/soffice.exe",
        "/mnt/c/Program Files (x86)/LibreOffice/program/soffice.exe",
    ):
        if Path(p).exists():
            return p
    return None


def find_pdftoppm():
    if shutil.which("pdftoppm"):
        return "pdftoppm"
    return None


def pptx_to_pdf(pptx_path, work_dir):
    """LibreOffice headless로 .pptx → .pdf 변환. work_dir 안에 결과 저장."""
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice 없음 (soffice/libreoffice). "
            "Ubuntu: sudo apt install libreoffice. "
            "Windows: https://www.libreoffice.org/"
        )
    # LibreOffice는 Windows 경로 잘 처리하므로 src를 work_dir로 복사
    src = Path(pptx_path).resolve()
    dst = Path(work_dir) / src.name
    shutil.copy2(src, dst)
    # LibreOffice Windows 빌드는 WSL 경로(/tmp/...) 인식 못 함 → cwd 기반으로 동작
    proc = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", dst.name],
        capture_output=True, text=True, timeout=120, cwd=str(work_dir)
    )
    pdf_path = Path(work_dir) / (src.stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(
            f"PDF 변환 실패. soffice={soffice}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return pdf_path


def pdf_to_pngs(pdf_path, out_dir, dpi=80):
    """pdftoppm으로 PDF → 페이지별 PNG. out_dir/slide_NN.png 생성."""
    if not find_pdftoppm():
        raise RuntimeError(
            "pdftoppm 없음 (poppler-utils). "
            "Ubuntu: sudo apt install poppler-utils"
        )
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    prefix = Path(out_dir) / "slide"
    proc = subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(prefix)],
        capture_output=True, text=True, timeout=120
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pdftoppm 실패: {proc.stderr}")
    pngs = sorted(Path(out_dir).glob("slide-*.png"))
    # slide-01.png → slide_01.png 로 통일 (사람·셸 친화)
    renamed = []
    for p in pngs:
        # pdftoppm 기본 포맷: slide-01.png, slide-02.png ...
        new_name = p.name.replace("slide-", "slide_")
        new_path = p.parent / new_name
        if p != new_path:
            p.rename(new_path)
            renamed.append(new_path)
        else:
            renamed.append(p)
    return renamed


def render(pptx_path, out_dir=None, dpi=80):
    """전체 렌더 파이프라인. (pptx → pdf → png NNN개)"""
    pptx_path = Path(pptx_path).resolve()
    if not pptx_path.exists():
        raise FileNotFoundError(f"템플릿 없음: {pptx_path}")
    if out_dir is None:
        out_dir = pptx_path.parent / f"{pptx_path.stem}.thumbnails"
    out_dir = Path(out_dir).resolve()

    with tempfile.TemporaryDirectory(prefix="dsi_thumb_") as tmp:
        pdf = pptx_to_pdf(pptx_path, tmp)
        pngs = pdf_to_pngs(pdf, out_dir, dpi=dpi)
    return out_dir, pngs


def main():
    if len(sys.argv) < 2:
        print("사용: python3 scripts/render_thumbnails.py <template.pptx> [<out_dir>]",
              file=sys.stderr)
        sys.exit(1)
    pptx_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) >= 3 else None
    dpi = int(os.environ.get("DSI_THUMB_DPI", "80"))

    try:
        out, pngs = render(pptx_path, out_dir, dpi=dpi)
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(2)

    print(f"렌더 완료: {len(pngs)} 페이지", file=sys.stderr)
    print(f"경로: {out}", file=sys.stderr)
    for p in pngs:
        print(f"  {p.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
