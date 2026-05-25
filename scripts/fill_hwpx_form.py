#!/usr/bin/env python3
"""HWPX 양식 + fills.yaml → 채워진 .hwpx (XML 결정적 편집).

원칙 (memory/feedback_xml_fill.md, feedback_form_principle.md):
    양식 절대 안 만짐. 빈 셀에 텍스트만 박음.
    한컴 COM 미사용. zip + lxml 만으로 결정적 동작.

용법:
    python scripts/fill_hwpx_form.py <form.hwpx> <fills.yaml> <output.hwpx>

fills.yaml 스키마:
    fills:
      - id: T{table_idx}_R{row}_C{col}
        text: "채울 텍스트"

알고리즘:
    1. .hwpx zip 풀어 Contents/section*.xml 파싱
    2. hp:tbl 순서대로 table_idx 부여 (0-based)
    3. 각 hp:tc 의 hp:cellAddr 로 (row, col) 확인
    4. fills 명세와 id 매칭, 매칭 셀의 첫 hp:p > hp:run > hp:t 텍스트 박음
       (없으면 hp:t 신설)
    5. zip 다시 묶음. 다른 파일·메타 변경 없음.

일반화:
    표/셀 좌표는 hp:cellAddr 명시값 사용. 양식 종류 무관.
    fills.yaml id 형식만 맞으면 동작.
"""
import re
import sys
import shutil
import tempfile
import zipfile
import yaml
from pathlib import Path
from lxml import etree


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hp": HP_NS}
CELL_ID_RE = re.compile(r"^T(\d+)_R(\d+)_C(\d+)$")
CELL_PARA_ID_RE = re.compile(r"^T(\d+)_R(\d+)_C(\d+)_P(\d+)$")
PARA_ID_RE = re.compile(r"^P(\d+)$")


def parse_cell_id(cell_id: str):
    m = CELL_ID_RE.match(cell_id)
    if not m:
        raise ValueError(f"잘못된 cell id: {cell_id!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def parse_cell_para_id(cid: str):
    m = CELL_PARA_ID_RE.match(cid)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def parse_para_id(pid: str):
    m = PARA_ID_RE.match(pid)
    if not m:
        return None
    return int(m.group(1))


def build_cell_index(section_root):
    """section XML 안의 모든 표·셀을 (table_idx, row, col) → hp:tc element 로 매핑.

    table_idx 는 *문서 순서대로 등장하는 hp:tbl 의 0-based 인덱스*.
    row, col 은 hp:cellAddr 의 rowAddr/colAddr 명시값.
    """
    index = {}
    tables = section_root.iter(f"{{{HP_NS}}}tbl")
    for t_idx, tbl in enumerate(tables):
        for tr in tbl.findall(f"{{{HP_NS}}}tr"):
            for tc in tr.findall(f"{{{HP_NS}}}tc"):
                addr = tc.find(f"{{{HP_NS}}}cellAddr")
                if addr is None:
                    continue
                row = int(addr.get("rowAddr"))
                col = int(addr.get("colAddr"))
                index[(t_idx, row, col)] = tc
    return index


def set_cell_text(tc_el, text: str):
    """hp:tc 안 첫 hp:p > hp:run > hp:t 의 텍스트 *통째 교체*.

    주의: 양식 원본 텍스트 (라벨 등) 도 통째로 덮어씀.
    체크박스 셀처럼 원본 일부만 바꾸려면 set_cell_text_partial 사용.
    """
    subList = tc_el.find(f"{{{HP_NS}}}subList")
    if subList is None:
        return False
    p = subList.find(f"{{{HP_NS}}}p")
    if p is None:
        p = etree.SubElement(subList, f"{{{HP_NS}}}p")
    run = p.find(f"{{{HP_NS}}}run")
    if run is None:
        run = etree.SubElement(p, f"{{{HP_NS}}}run")
    t = run.find(f"{{{HP_NS}}}t")
    if t is None:
        t = etree.SubElement(run, f"{{{HP_NS}}}t")
    t.text = text
    return True


def apply_cell_check(tc_el, mode: str = "check"):
    """체크박스 셀의 *원본 텍스트 보존* + □/☐ → ☑ (또는 ☑/☒ → □) 만 부분 교체.

    양식 라벨 절대 안 변경. 예: "□ 여" → "☑ 여" (라벨 "여" 보존).
    """
    subList = tc_el.find(f"{{{HP_NS}}}subList")
    if subList is None:
        return False
    changed = False
    for t in tc_el.iter(f"{{{HP_NS}}}t"):
        if t.text is None:
            continue
        if mode == "check":
            new = t.text.replace("□", "☑").replace("☐", "☑")
        elif mode == "uncheck":
            new = t.text.replace("☑", "□").replace("☒", "□")
        else:
            new = t.text
        if new != t.text:
            t.text = new
            changed = True
    return changed


def build_paragraph_index(section_root):
    """최상위 hp:p 만 → p_idx → hp:p element 매핑."""
    return {i: p for i, p in enumerate(section_root.findall(f"{{{HP_NS}}}p"))}


def set_paragraph_text(p_el, text: str):
    """hp:p 안 첫 hp:run 의 hp:t 텍스트 교체. linesegarray 삭제 (한컴 재계산).

    여러 줄 text 는 첫 줄만 박음 (단순 PoC). 본격은 hp:p 통째 복제 + 다중 단락.
    """
    run = p_el.find(f"{{{HP_NS}}}run")
    if run is None:
        return False
    t = run.find(f"{{{HP_NS}}}t")
    if t is None:
        t = etree.SubElement(run, f"{{{HP_NS}}}t")
    t.text = text
    ls = p_el.find(f"{{{HP_NS}}}linesegarray")
    if ls is not None:
        p_el.remove(ls)
    return True


def fill_section(section_path: Path, fills: list, stats: dict):
    """section XML 파일을 in-place 편집. fills 적용 + stats 갱신."""
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(section_path), parser)
    root = tree.getroot()
    cell_idx = build_cell_index(root)
    para_idx = build_paragraph_index(root)
    stats["sections_total"] = stats.get("sections_total", 0) + 1
    stats["cells_in_section"] = stats.get("cells_in_section", 0) + len(cell_idx)
    stats["paras_in_section"] = stats.get("paras_in_section", 0) + len(para_idx)

    for entry in fills:
        cid = entry.get("id", "")
        operation = entry.get("operation", "replace_text")
        text = entry.get("text", "")
        if not cid:
            continue
        if operation == "replace_text" and text == "":
            continue

        cp_match = parse_cell_para_id(cid)
        if cp_match is not None:
            t, r, c, p_sub = cp_match
            tc = cell_idx.get((t, r, c))
            if tc is None:
                continue
            sub = tc.find(f"{{{HP_NS}}}subList")
            if sub is None:
                continue
            ps = sub.findall(f"{{{HP_NS}}}p")
            if p_sub < len(ps) and set_paragraph_text(ps[p_sub], str(text)):
                stats["filled_cellpara"] = stats.get("filled_cellpara", 0) + 1
            continue

        p_match = parse_para_id(cid)
        if p_match is not None:
            p_el = para_idx.get(p_match)
            if p_el is not None and set_paragraph_text(p_el, str(text)):
                stats["filled_para"] = stats.get("filled_para", 0) + 1
            continue
        try:
            t, r, c = parse_cell_id(cid)
        except ValueError:
            stats["failed_id"] = stats.get("failed_id", 0) + 1
            continue
        tc = cell_idx.get((t, r, c))
        if tc is None:
            continue
        if operation in ("check", "uncheck"):
            if apply_cell_check(tc, operation):
                stats["filled_check"] = stats.get("filled_check", 0) + 1
        else:
            if set_cell_text(tc, str(text)):
                stats["filled_cell"] = stats.get("filled_cell", 0) + 1

    body = etree.tostring(root, encoding="unicode")
    header = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    section_path.write_bytes((header + body).encode("utf-8"))


def fill_hwpx(form_path: str, fills_path: str, out_path: str):
    fills_data = yaml.safe_load(Path(fills_path).read_text(encoding="utf-8"))
    fills = fills_data.get("fills", [])
    if not fills:
        print("WARN: fills 비어있음", file=sys.stderr)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with zipfile.ZipFile(form_path, "r") as zin:
            zin.extractall(td_path)

        section_dir = td_path / "Contents"
        section_files = sorted(section_dir.glob("section*.xml"))
        if not section_files:
            raise RuntimeError(f"section*.xml 없음: {section_dir}")

        stats = {"filled": 0}
        for sf in section_files:
            fill_section(sf, fills, stats)

        out_abs = Path(out_path).resolve()
        if out_abs.exists():
            out_abs.unlink()
        with zipfile.ZipFile(out_abs, "w", zipfile.ZIP_DEFLATED) as zout:
            mime = td_path / "mimetype"
            if mime.exists():
                zout.write(mime, "mimetype", zipfile.ZIP_STORED)
            for f in td_path.rglob("*"):
                if not f.is_file() or f == mime:
                    continue
                arc = f.relative_to(td_path).as_posix()
                zout.write(f, arc)

    print(f"채움: 셀 {stats.get('filled_cell', 0)} + 단락 {stats.get('filled_para', 0)} + 셀안단락 {stats.get('filled_cellpara', 0)} + 체크 {stats.get('filled_check', 0)} / 총 {len(fills)} 명세", file=sys.stderr)
    print(f"저장: {out_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 4:
        print("사용: python scripts/fill_hwpx_form.py <form.hwpx> <fills.yaml> <output.hwpx>")
        sys.exit(1)
    fill_hwpx(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
