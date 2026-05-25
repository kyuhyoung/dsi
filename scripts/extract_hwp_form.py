#!/usr/bin/env python3
"""HWP 양식(.hwp) → 셀 구조 + 빈 셀 식별 (yaml) 추출.

원칙 (memory/feedback_form_principle.md):
    양식은 절대 만지지 않는다. 빈 셀에 텍스트만 박는다.
    → 여기서는 *visual 정보 추출 금지*. 셀 구조 + 식별자 + hint만.

용법:
    python3 scripts/extract_hwp_form.py <form.hwp> [output.form.yaml]

산출 yaml:
    title: <문서 제목>
    table_count: N
    tables:
      - idx: 0
        rows: R, cols: C
        cells:
          - id: T0_R0_C0
            row: 0, col: 0
            text: '구분'
            colspan: 1, rowspan: 1
            is_empty: false        # text 가 비어있으면 true
          - id: T0_R0_C1
            row: 0, col: 1
            text: ''
            colspan: 1, rowspan: 1
            is_empty: true
            hints:
              left: '구분'                  # 같은 행 왼쪽 가장 가까운 비어있지 않은 셀
              up: ''                        # 같은 열 위쪽 가장 가까운 비어있지 않은 셀
              table_label: '구분'           # 같은 표의 첫 비어있지 않은 셀 (헤더)
              table_caption: '회사 개요'    # 표 직전 단락 텍스트
    fill_targets:
      - id: T0_R0_C1
        hints: {left: '구분', up: '', table_label: '구분', table_caption: '회사 개요'}
      - ...

알고리즘만. 의미 해석은 LLM(proposal-writer)이 hints 보고 결정.
"""
import sys
import subprocess
import yaml
from pathlib import Path
from lxml import etree


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


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


def build_table(t_idx, table_el, prev_para_text):
    """TableControl → table dict (idx, rows, cols, cells)."""
    body = table_el.find(".//TableBody")
    if body is None:
        return None

    rows = []
    for r_idx, row in enumerate(body.findall("TableRow")):
        cells = []
        for c_idx, cell in enumerate(row.findall("TableCell")):
            col_addr = cell.get("col-addr") or cell.get("col") or str(c_idx)
            row_addr = cell.get("row-addr") or cell.get("row") or str(r_idx)
            colspan = cell.get("col-span") or "1"
            rowspan = cell.get("row-span") or "1"
            cells.append({
                "row": int(row_addr) if row_addr.isdigit() else r_idx,
                "col": int(col_addr) if col_addr.isdigit() else c_idx,
                "text": text_of(cell),
                "colspan": int(colspan) if colspan.isdigit() else 1,
                "rowspan": int(rowspan) if rowspan.isdigit() else 1,
            })
        rows.append(cells)

    if not rows:
        return None

    flat = [c for row in rows for c in row]

    table_label = next((c["text"] for c in flat if c["text"]), "")

    for c in flat:
        c["id"] = f"T{t_idx}_R{c['row']}_C{c['col']}"
        c["is_empty"] = c["text"] == ""

    for c in flat:
        if not c["is_empty"]:
            continue
        left_cands = [o for o in flat if o["row"] == c["row"] and o["col"] < c["col"] and o["text"]]
        up_cands = [o for o in flat if o["col"] == c["col"] and o["row"] < c["row"] and o["text"]]
        c["hints"] = {
            "left": max(left_cands, key=lambda x: x["col"])["text"] if left_cands else "",
            "up": max(up_cands, key=lambda x: x["row"])["text"] if up_cands else "",
            "table_label": table_label,
            "table_caption": prev_para_text,
        }

    return {
        "idx": t_idx,
        "rows": len(rows),
        "cols": max((len(r) for r in rows), default=0),
        "cells": flat,
    }


def analyze_form(hwp_path):
    xml_bytes = extract_xml(hwp_path)
    root = etree.fromstring(xml_bytes)

    title = ""
    for prop in root.iter("Property"):
        if prop.get("id-label") == "PIDSI_TITLE":
            title = prop.get("value", "")
            break

    page_breaks = []
    section_breaks = []
    for para in root.iter("Paragraph"):
        para_id = para.get("paragraph-id")
        if para.get("new-page") == "1":
            page_breaks.append(int(para_id) if para_id and para_id.isdigit() else -1)
        if para.get("new-section") == "1":
            section_breaks.append(int(para_id) if para_id and para_id.isdigit() else -1)

    tables = []
    prev_para_text = ""
    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag == "Paragraph":
            txt = text_of(el).strip()
            if txt and not el.findall(".//TableControl"):
                prev_para_text = txt
        elif tag == "TableControl":
            t = build_table(len(tables), el, prev_para_text)
            if t:
                tables.append(t)

    para_count = sum(1 for _ in root.iter("Paragraph"))

    fill_targets = []
    for t in tables:
        for c in t["cells"]:
            if c["is_empty"]:
                fill_targets.append({
                    "id": c["id"],
                    "hints": c["hints"],
                })

    return {
        "_extracted_from": str(hwp_path),
        "_purpose": "양식 셀 구조 + 빈 셀 식별 + hint. proposal-writer 가 fill_targets 보고 fills 작성.",
        "_principle": "양식 절대 안 만짐. visual 정보 추출 안 함. 빈 셀에 텍스트만 박을 명세 산출.",
        "title": title,
        "paragraph_count": para_count,
        "table_count": len(tables),
        "page_break_count": len(page_breaks),
        "section_break_count": len(section_breaks),
        "page_breaks_at_paragraph": page_breaks,
        "section_breaks_at_paragraph": section_breaks,
        "fill_target_count": len(fill_targets),
        "tables": tables,
        "fill_targets": fill_targets,
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
        yaml.dump(data, f, Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"저장: {out_path}", file=sys.stderr)
    print(f"  표: {data['table_count']}개, 빈 셀(fill_targets): {data['fill_target_count']}개", file=sys.stderr)


if __name__ == "__main__":
    main()
