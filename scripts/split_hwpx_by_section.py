#!/usr/bin/env python3
"""통합 .hwpx + form.yaml(sections) → 별지별 .hwpx 분리.

원칙 (memory):
    - 양식 절대 안 만짐 (원본 visual 보존)
    - 한컴 COM 미사용 — XML 결정적 분할
    - 임의 양식 동작 — 농식품AI 하드코딩 0
    - 산출물은 output 폴더 (Temp 금지)

용법:
    python scripts/split_hwpx_by_section.py <form.hwpx> <form.yaml> <output_dir>

각 별지마다:
    output_dir/<safe_label>.hwpx 생성
    label 안전화: 공백→_, 특수문자→_, 윈도 금지 문자 제거

알고리즘:
    1. 통합 .hwpx zip 풀기
    2. section0.xml 의 hp:p 트리에서 *해당 별지 paragraph_range* 만 남김
    3. 첫 hp:p (hp:secPr 보유) 는 항상 keep — 페이지 설정·헤더/풋터 정의
    4. zip 다시 묶음 → 새 .hwpx
    5. header.xml·BinData·META-INF 그대로 (해당 별지에 안 쓰여도 OK, 낭비지만 안전)
"""
import re
import sys
import yaml
import shutil
import tempfile
import zipfile
from pathlib import Path
from lxml import etree
from copy import deepcopy


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"


def safe_filename(label: str) -> str:
    """별지 라벨 → 윈도 안전 파일명."""
    s = re.sub(r"[\\/:*?\"<>|]", "", label)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:80] or "section"


def extract_section(form_hwpx: Path, p_start: int, p_end, out_path: Path):
    """form.hwpx 에서 paragraph_range [p_start, p_end) 만 남긴 .hwpx 생성."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with zipfile.ZipFile(str(form_hwpx), "r") as zin:
            zin.extractall(td_path)

        sec_files = sorted((td_path / "Contents").glob("section*.xml"))
        if not sec_files:
            raise RuntimeError("section*.xml 없음")
        sec = sec_files[0]

        tree = etree.parse(str(sec))
        root = tree.getroot()
        top_ps = root.findall(f"{{{HP_NS}}}p")

        first_p = top_ps[0] if top_ps else None
        range_end = len(top_ps) if p_end is None else p_end
        keep_set = set(range(p_start, range_end))
        if first_p is not None:
            keep_set.add(0)

        for i, p in enumerate(top_ps):
            if i not in keep_set:
                root.remove(p)

        body = etree.tostring(root, encoding="unicode")
        header = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        sec.write_bytes((header + body).encode("utf-8"))

        if out_path.exists():
            out_path.unlink()
        with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as zout:
            mime = td_path / "mimetype"
            if mime.exists():
                zout.write(str(mime), "mimetype", zipfile.ZIP_STORED)
            for f in td_path.rglob("*"):
                if not f.is_file() or f == mime:
                    continue
                zout.write(str(f), f.relative_to(td_path).as_posix())


def main():
    if len(sys.argv) < 4:
        print("사용: python scripts/split_hwpx_by_section.py <form.hwpx> <form.yaml> <output_dir>")
        sys.exit(1)
    form_hwpx = Path(sys.argv[1])
    form_yaml = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    data = yaml.safe_load(form_yaml.read_text(encoding="utf-8"))
    sections = data.get("sections", [])
    if not sections:
        print("ERR: sections 비어있음 (form.yaml 확인)", file=sys.stderr)
        sys.exit(1)

    print(f"분리: {len(sections)} 별지", file=sys.stderr)
    for i, s in enumerate(sections):
        p_start, p_end = s["paragraph_range"]
        fname = f"{i+1:02d}_{safe_filename(s['label'])}.hwpx"
        out_path = out_dir / fname
        try:
            extract_section(form_hwpx, p_start, p_end, out_path)
            size = out_path.stat().st_size
            print(f"  {fname} ({size:,} B) p{p_start}~{p_end}", file=sys.stderr)
        except Exception as e:
            print(f"  ERR {fname}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
