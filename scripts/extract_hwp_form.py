#!/usr/bin/env python3
"""HWP 양식(.hwp) → 시각 양식 구조 (yaml) 추출.

용법:
    python3 scripts/extract_hwp_form.py <form.hwp> [output.form.yaml]

원리:
    hwp5proc xml 로 .hwp → XML 추출 후 *표·셀·서식* 정보를 yaml로 구조화.
    LLM(form-analyst agent)이 yaml과 텍스트를 함께 보고 *시각 양식 의미*를 분석.

산출 yaml 구조:
    title: <문서 제목>
    paragraphs: <단락 수>
    tables:
      - idx: 0
        rows: 3
        cols: 5
        cells:
          - row: 0
            col: 0
            text: '구분'
            colspan: 1
            rowspan: 1
        position_hint: <문맥 텍스트 (앞 단락)>

알고리즘만. 의미 해석은 LLM.
"""
import sys
import subprocess
import yaml
from pathlib import Path
from lxml import etree


def extract_xml(hwp_path):
    """hwp5proc xml <hwp> 호출."""
    result = subprocess.run(
        ["hwp5proc", "xml", hwp_path],
        capture_output=True, check=True, timeout=60
    )
    return result.stdout


def text_of(el):
    """element 안의 모든 <Text> 노드 텍스트 합침."""
    parts = []
    for t in el.iter():
        if t.tag.endswith("Text") and t.text:
            parts.append(t.text)
    return "".join(parts).strip()


def extract_borderfills(root):
    """DocInfo 안 BorderFill 정의를 id별 dict로 추출.

    반환: {id: {background_color, has_fill, pattern_color, border_color}}
    """
    fills = {}
    for idx, bf in enumerate(root.iter("BorderFill")):
        # 일부 BorderFill 은 borderfill-id 가 없고 *순서대로 1, 2, 3...* (hwp5proc 출력 기준)
        # 따라서 등장 순서를 id로 사용. 인덱스는 1부터 시작 (hwp 관례).
        bf_id = bf.get("borderfill-id") or str(idx)
        fcp = bf.find(".//FillColorPattern")
        bg = fcp.get("background-color") if fcp is not None else None
        pattern = fcp.get("pattern-color") if fcp is not None else None
        # fillflags 가 "00000000" 이면 fill 없음
        flags = bf.get("fillflags", "00000000")
        has_fill = flags != "00000000"
        # 첫 Border 의 color 를 대표 border color 로
        border_el = bf.find("Border")
        border_color = border_el.get("color") if border_el is not None else "#000000"

        entry = {
            "has_fill": has_fill,
            "background_color": bg,
            "pattern_color": pattern,
            "border_color": border_color,
        }
        # 순서 id (1부터) 와 명시적 id 둘 다 저장
        fills[str(idx)] = entry
        if bf.get("borderfill-id"):
            fills[bf.get("borderfill-id")] = entry
    return fills


def extract_charshapes(root):
    """DocInfo 안 CharShape 정의를 id별 dict로 추출.

    반환: {id: {bold, italic, text_color, shade_color}}
    """
    shapes = {}
    for idx, cs in enumerate(root.iter("CharShape")):
        cs_id = cs.get("charshape-id") or str(idx)
        entry = {
            "bold": cs.get("bold") == "1",
            "italic": cs.get("italic") == "1",
            "text_color": cs.get("text-color"),
            "shade_color": cs.get("shade-color"),
        }
        shapes[str(idx)] = entry
        if cs.get("charshape-id"):
            shapes[cs.get("charshape-id")] = entry
    return shapes


def cell_visual(cell, borderfills, charshapes):
    """TableCell 의 시각 정보 추출.

    - borderfill-id-list: 셀별 BorderFill 참조
    - 셀 안 첫 Text 의 paragraph charshape-id
    """
    visual = {}
    # 셀 BorderFill (배경색·테두리)
    # hwp XML 에서 TableCell 은 'borderfill-id-list' 또는 단일 'borderfill-id' 가짐
    bf_ref = cell.get("borderfill-id") or cell.get("borderfill-id-list")
    if bf_ref:
        # list 형태면 첫 번째 사용
        bf_id = bf_ref.split()[0] if " " in bf_ref else bf_ref
        bf_entry = borderfills.get(bf_id)
        if bf_entry:
            if bf_entry["has_fill"] and bf_entry["background_color"]:
                visual["background_color"] = bf_entry["background_color"]
            visual["border_color"] = bf_entry["border_color"]

    # 첫 paragraph의 char-shape-id (셀 안 텍스트 굵기·색)
    first_para = cell.find(".//Paragraph")
    if first_para is not None:
        cs_id = first_para.get("char-shape-id") or first_para.get("charshape-id")
        if cs_id:
            cs_entry = charshapes.get(cs_id)
            if cs_entry:
                if cs_entry["bold"]:
                    visual["bold"] = True
                if cs_entry["italic"]:
                    visual["italic"] = True
                if cs_entry["text_color"] and cs_entry["text_color"] != "#000000":
                    visual["text_color"] = cs_entry["text_color"]
    return visual


def analyze_form(hwp_path):
    """hwp 파일 → 양식 구조 dict (표 + 페이지 break + 시각 정보)."""
    xml_bytes = extract_xml(hwp_path)
    root = etree.fromstring(xml_bytes)

    # 문서 제목
    title = ""
    for prop in root.iter("Property"):
        if prop.get("id-label") == "PIDSI_TITLE":
            title = prop.get("value", "")
            break

    # 시각 정의 추출 (BorderFill·CharShape)
    borderfills = extract_borderfills(root)
    charshapes = extract_charshapes(root)

    # 페이지·섹션 break 위치 (단락 번호 기준)
    page_breaks = []         # paragraph-id list with new-page=1
    section_breaks = []      # paragraph-id list with new-section=1
    for para in root.iter("Paragraph"):
        para_id = para.get("paragraph-id")
        if para.get("new-page") == "1":
            page_breaks.append(int(para_id) if para_id and para_id.isdigit() else -1)
        if para.get("new-section") == "1":
            section_breaks.append(int(para_id) if para_id and para_id.isdigit() else -1)

    # 표 list
    tables = []
    for t_idx, table in enumerate(root.iter("TableControl")):
        body = table.find(".//TableBody")
        if body is None:
            continue
        rows_data = []
        for r_idx, row in enumerate(body.findall("TableRow")):
            cells_data = []
            for c_idx, cell in enumerate(row.findall("TableCell")):
                cell_text = text_of(cell)
                col_addr = cell.get("col-addr") or cell.get("col") or str(c_idx)
                row_addr = cell.get("row-addr") or cell.get("row") or str(r_idx)
                colspan = cell.get("col-span") or "1"
                rowspan = cell.get("row-span") or "1"
                visual = cell_visual(cell, borderfills, charshapes)
                cell_data = {
                    "row": int(row_addr) if row_addr.isdigit() else r_idx,
                    "col": int(col_addr) if col_addr.isdigit() else c_idx,
                    "text": cell_text,
                    "colspan": int(colspan) if colspan.isdigit() else 1,
                    "rowspan": int(rowspan) if rowspan.isdigit() else 1,
                }
                if visual:
                    cell_data["visual"] = visual
                cells_data.append(cell_data)
            rows_data.append(cells_data)
        if rows_data:
            tables.append({
                "idx": t_idx,
                "rows": len(rows_data),
                "cols": max((len(r) for r in rows_data), default=0),
                "cells": [c for row in rows_data for c in row],
            })

    # 단락 수
    para_count = sum(1 for _ in root.iter("Paragraph"))

    return {
        "_extracted_from": str(hwp_path),
        "_purpose": "시각 양식 구조 + 셀별 시각 정보 (background_color·bold·text_color). form-analyst agent (LLM)가 의미 해석.",
        "title": title,
        "paragraph_count": para_count,
        "table_count": len(tables),
        "page_break_count": len(page_breaks),
        "section_break_count": len(section_breaks),
        "page_breaks_at_paragraph": page_breaks,
        "section_breaks_at_paragraph": section_breaks,
        "borderfill_count": len(set(borderfills.keys())),
        "charshape_count": len(set(charshapes.keys())),
        "tables": tables,
    }


def main():
    if len(sys.argv) < 2:
        print("사용: python3 scripts/extract_hwp_form.py <form.hwp> [output.form.yaml]")
        sys.exit(1)
    hwp_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) >= 3 else hwp_path[:-len(".hwp")] + ".form.yaml"

    print(f"추출 중: {hwp_path}", file=sys.stderr)
    data = analyze_form(hwp_path)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"저장: {out_path}", file=sys.stderr)
    print(f"  표: {data['table_count']}개, 단락: {data['paragraph_count']}개", file=sys.stderr)


if __name__ == "__main__":
    main()
