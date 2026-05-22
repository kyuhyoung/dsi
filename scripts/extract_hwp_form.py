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


def analyze_form(hwp_path):
    """hwp 파일 → 양식 구조 dict (표 + 페이지 break)."""
    xml_bytes = extract_xml(hwp_path)
    root = etree.fromstring(xml_bytes)

    # 문서 제목
    title = ""
    for prop in root.iter("Property"):
        if prop.get("id-label") == "PIDSI_TITLE":
            title = prop.get("value", "")
            break

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
        # TableBody 안에 TableRow → TableCell 구조
        body = table.find(".//TableBody")
        if body is None:
            continue
        rows_data = []
        for r_idx, row in enumerate(body.findall("TableRow")):
            cells_data = []
            for c_idx, cell in enumerate(row.findall("TableCell")):
                # 셀 안 텍스트 추출
                cell_text = text_of(cell)
                col_addr = cell.get("col-addr") or cell.get("col") or str(c_idx)
                row_addr = cell.get("row-addr") or cell.get("row") or str(r_idx)
                colspan = cell.get("col-span") or "1"
                rowspan = cell.get("row-span") or "1"
                cells_data.append({
                    "row": int(row_addr) if row_addr.isdigit() else r_idx,
                    "col": int(col_addr) if col_addr.isdigit() else c_idx,
                    "text": cell_text,
                    "colspan": int(colspan) if colspan.isdigit() else 1,
                    "rowspan": int(rowspan) if rowspan.isdigit() else 1,
                })
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
        "_purpose": "시각 양식 구조. form-analyst agent (LLM)가 보고 의미 해석.",
        "title": title,
        "paragraph_count": para_count,
        "table_count": len(tables),
        "page_break_count": len(page_breaks),
        "section_break_count": len(section_breaks),
        "page_breaks_at_paragraph": page_breaks,
        "section_breaks_at_paragraph": section_breaks,
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
