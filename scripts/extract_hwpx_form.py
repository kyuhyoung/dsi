#!/usr/bin/env python3
"""HWPX 양식 → 셀 구조 + 빈 셀 + 별지 분할 (yaml).

원칙 (memory):
    - 양식 절대 안 만짐 (feedback_form_principle)
    - 한컴 COM은 .hwp→.hwpx 변환에만 1회 (feedback_xml_fill)
    - 산출물은 본체 별지 1개 (feedback_main_separator)
    - 임의 A·B·C 동작 — 양식 종류·도메인·사업명 하드코딩 X (feedback_no_overfit)

용법:
    python scripts/extract_hwpx_form.py <form.hwp|.hwpx> [output.form.yaml]

산출 yaml (스키마):
    title: <문서 제목>
    table_count: N
    sections:
      - label: '[별지 제1호] 자가진단서'   # 한국 공공 RFP 별지 마커
        paragraph_range: [0, 10]
        table_idx_range: [0, 2]
        cell_count: 47
        empty_cell_count: 10
      - label: '[별지 제3호] 사업계획서'   # 보통 본체
        paragraph_range: [120, 800]
        table_idx_range: [13, 67]
        cell_count: 800
        empty_cell_count: 450
    tables:
      - idx, rows, cols, cells: [{id: T{n}_R{r}_C{c}, row, col, text, colspan, rowspan, is_empty, hints, section_label}]
    fill_targets:
      - {id, hints, section_label}    # section_label 로 본체 필터 가능

별지 마커 패턴 (한국 공공 RFP 표준):
    `[별지 제N호]`, `[별 지 제N호]`, `[붙임 N]`, `붙임 N` 등.
    정규식: r'\[?\s*(별\s*지|붙\s*임)\s*제?\s*\d+\s*호?\s*\]?'
"""
import re
import sys
import shutil
import subprocess
import tempfile
import zipfile
import yaml
from pathlib import Path
from lxml import etree


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"
NS = {"hp": HP_NS, "hs": HS_NS}

SECTION_MARKER_RE = re.compile(
    # 별지/붙임/첨부 + 제?N(-M)?호? — 하이픈 서브넘버 (예: 제2-2호, 제2-3호) 지원.
    # 한국 양식 관행: 큰 별지 한 호가 -1·-2 등 서브로 나뉘는 경우 잦음.
    r"\[?\s*(별\s*지|붙\s*임|첨\s*부)\s*제?\s*\d+(?:\s*-\s*\d+)?\s*호?\s*\]?",
    re.MULTILINE,
)

PLACEHOLDER_RE = re.compile(
    r"^\s*[○\-\*·\u25CF\u25CB\u25E6\u274D\u274C\u25A0\u25A1]?\s*(가나다|ㅇㅇ+|[XＸxｘ]{2,}|예시\s*내용|내용\s*작성|여기에\s*작성|작성하시오|\(작성\))\s*$"
)
# 작성요령(안내) 박스 식별 정규식 — *yaml 정본*: system_defaults.yaml.hwpx_fill.instruction_hint_pattern.
# fallback 패턴은 한국 양식 ※ 관행. _load_extract_patterns()가 yaml 값으로 덮어씀.
INSTRUCTION_HINT_RE = re.compile(r"^\s*※")
HEADER_RE = re.compile(r"^\s*([0-9]+[\.\-][0-9]+|[가-힣]\.)\s*")
# 체크박스 셀 식별 — 셀 텍스트 안에 체크박스 문자 하나라도 있으면 체크박스 셀로 판정.
# 라벨 길이·괄호·줄바꿈·복수 체크박스(□ 여 / □ 부) 모두 허용.
# 한컴이 쓰는 변형 포함: 빈/체크 사각·체크표·검은 사각·반쪽 사각.
CHECKBOX_RE = re.compile(r"[□☐☑☒✓✔■▣◧◨]")
EXAMPLE_RE = re.compile(
    r"(0+\.?0*\.?0+|OO법인|OO\s|XX법인|A주식회사|B주식회사|예시:|\(예\)|\([0-9]+\s*社\))"
)
SUBORDINATE_RE = re.compile(r"^\s*\u21B3")
INSTRUCTION_PLACEHOLDER_RE = re.compile(
    r"^[\*※○]\s+.{2,80}(명칭|작성|기재|소개|삽입|입력|쓰시오|적으시오|개수|매출|건수)\s*$"
)
# 표 안 생략 행 (terminator) — fallback. yaml 정본: system_defaults.yaml.hwpx_fill.form_patterns.table_row_ellipsis
TABLE_ROW_ELLIPSIS_RE = re.compile(r"^[\s·\.…]+$")
# 표 안 예시 행 감지 정책 — fallback. yaml 정본: system_defaults.yaml.hwpx_fill.example_row_detection
EXAMPLE_ROW_POLICY = {
    "enabled": True,
    "min_empty_data_rows": 1,
    "require_terminator": False,
    "max_example_rows": 3,
    "min_table_rows": 3,
    "min_table_cols": 2,
    "require_example_cell_in_candidate": True,
}


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _load_extract_patterns(project_root: Path = None):
    """templates/system_defaults.yaml 의 hwpx_fill 정본 패턴으로 *모든* 양식 인식 정규식 갱신.
    원본 코드의 정규식들은 *yaml 로드 실패 안전망* (한국 양식 fallback). yaml 정본이 우선.
    새 양식·표기는 *yaml만* 수정 — 코드 변경 0.
    """
    global INSTRUCTION_HINT_RE, SECTION_MARKER_RE
    global PLACEHOLDER_RE, HEADER_RE, CHECKBOX_RE
    global EXAMPLE_RE, SUBORDINATE_RE, INSTRUCTION_PLACEHOLDER_RE
    global TABLE_ROW_ELLIPSIS_RE, EXAMPLE_ROW_POLICY
    try:
        if project_root is None:
            project_root = Path(__file__).parent.parent
        cfg_path = project_root / "templates" / "system_defaults.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        hf = cfg.get("hwpx_fill") or {}
        # 안내 박스 패턴 (별도 키)
        if hf.get("instruction_hint_pattern"):
            INSTRUCTION_HINT_RE = re.compile(hf["instruction_hint_pattern"])
        # 양식 인식 정규식 그룹 (form_patterns)
        fp = hf.get("form_patterns") or {}
        if fp.get("section_marker"):
            SECTION_MARKER_RE = re.compile(fp["section_marker"], re.MULTILINE)
        if fp.get("placeholder"):
            PLACEHOLDER_RE = re.compile(fp["placeholder"])
        if fp.get("header"):
            HEADER_RE = re.compile(fp["header"])
        if fp.get("checkbox"):
            CHECKBOX_RE = re.compile(fp["checkbox"])
        if fp.get("example"):
            EXAMPLE_RE = re.compile(fp["example"])
        if fp.get("subordinate"):
            SUBORDINATE_RE = re.compile(fp["subordinate"])
        if fp.get("instruction_placeholder"):
            INSTRUCTION_PLACEHOLDER_RE = re.compile(fp["instruction_placeholder"])
        if fp.get("table_row_ellipsis"):
            TABLE_ROW_ELLIPSIS_RE = re.compile(fp["table_row_ellipsis"])
        # example_row_detection 정책 (hwpx_fill 직속)
        erd = hf.get("example_row_detection") or {}
        if erd:
            EXAMPLE_ROW_POLICY.update({k: v for k, v in erd.items() if k in EXAMPLE_ROW_POLICY})
    except Exception:
        pass  # fallback 유지


# 모듈 로드 시 패턴 갱신 (yaml 정본)
_load_extract_patterns()


def ensure_hwpx(in_path: str, tmp_root: Path) -> Path:
    """입력이 .hwp 면 한컴 COM 으로 .hwpx 변환 (1회). .hwpx 면 그대로."""
    p = Path(in_path)
    if p.suffix.lower() == ".hwpx":
        return p
    if p.suffix.lower() != ".hwp":
        raise ValueError(f"지원 안 함: {p.suffix} (.hwp/.hwpx)")
    out = tmp_root / (p.stem + ".hwpx")
    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "hwp_to_hwpx.py"), str(p.resolve()), str(out.resolve())],
        check=True,
    )
    return out


def text_of_p(p_el) -> str:
    """hp:p 안의 모든 hp:t 텍스트 합침."""
    parts = [t.text for t in p_el.iter(f"{{{HP_NS}}}t") if t.text]
    return "".join(parts).strip()


def text_of_tc(tc_el) -> str:
    parts = [t.text for t in tc_el.iter(f"{{{HP_NS}}}t") if t.text]
    return "".join(parts).strip()


def build_table(t_idx, tbl_el):
    rows = []
    for tr in tbl_el.findall(f"{{{HP_NS}}}tr"):
        cells = []
        for tc in tr.findall(f"{{{HP_NS}}}tc"):
            addr = tc.find(f"{{{HP_NS}}}cellAddr")
            span = tc.find(f"{{{HP_NS}}}cellSpan")
            row = int(addr.get("rowAddr")) if addr is not None else 0
            col = int(addr.get("colAddr")) if addr is not None else 0
            colspan = int(span.get("colSpan", "1")) if span is not None else 1
            rowspan = int(span.get("rowSpan", "1")) if span is not None else 1
            inner_ps = _collect_cell_paragraphs(tc)
            cells.append({
                "row": row, "col": col,
                "text": text_of_tc(tc),
                "colspan": colspan, "rowspan": rowspan,
                "inner_ps": inner_ps,
            })
        rows.append(cells)
    if not rows:
        return None

    flat = [c for row in rows for c in row]
    table_label = next((c["text"] for c in flat if c["text"]), "")
    for c in flat:
        c["id"] = f"T{t_idx}_R{c['row']}_C{c['col']}"
        c["is_empty"] = c["text"] == ""
        c["intent"] = _classify_cell_intent(c, table_label)
        inner_intents = [ip["intent"] for ip in c.get("inner_ps", [])]
        ph_count = inner_intents.count("placeholder")
        if ph_count >= 1 and c["intent"] in ("label_or_content", "checkbox", "instruction"):
            c["intent"] = "placeholder"
        elif "example" in inner_intents and c["intent"] == "label_or_content":
            c["intent"] = "example"

    # hints: *모든 셀* 에 생성 (이전엔 is_empty 만). example 셀·label_or_content 셀의
    # *값 자리* 도 빌더가 KB lookup 으로 채울 수 있게 — 임의 양식의 *예시 텍스트* 가
    # 양식 라벨 hint 갖도록 일반화. 빌더가 *_is_fillable* (빈/example/맥락) 로 채움.
    for c in flat:
        left_cands = [o for o in flat if o["row"] == c["row"] and o["col"] < c["col"] and o["text"]]
        up_cands = [o for o in flat if o["col"] == c["col"] and o["row"] < c["row"] and o["text"]]
        c["hints"] = {
            "left": max(left_cands, key=lambda x: x["col"])["text"] if left_cands else "",
            "up": max(up_cands, key=lambda x: x["row"])["text"] if up_cands else "",
            "table_label": table_label,
        }

    return {
        "idx": t_idx,
        "rows": len(rows),
        "cols": max((len(r) for r in rows), default=0),
        "cells": flat,
    }


def _collect_cell_paragraphs(tc_el):
    """hp:tc 안의 *모든* hp:p 를 (sub_idx, text, intent) 로 추출.

    셀 안 단락은 본문 placeholder 또는 안내·예시일 수 있음.
    한컴 hp:tc > hp:subList > hp:p > hp:run > hp:t 구조.
    """
    ps = []
    subList = tc_el.find(f"{{{HP_NS}}}subList")
    if subList is None:
        return ps
    for sub_idx, p in enumerate(subList.findall(f"{{{HP_NS}}}p")):
        txt = "".join(t.text for t in p.iter(f"{{{HP_NS}}}t") if t.text).strip()
        ps.append({
            "sub_idx": sub_idx,
            "text": txt,
            "intent": _classify_paragraph_intent(txt),
        })
    return ps


def _classify_paragraph_intent(text):
    """단락 텍스트 → intent (placeholder / instruction / example / header / content / empty)."""
    if not text:
        return "empty"
    if INSTRUCTION_HINT_RE.match(text):
        return "instruction"
    if PLACEHOLDER_RE.match(text):
        return "placeholder"
    if EXAMPLE_RE.search(text):
        return "example"
    if HEADER_RE.match(text):
        return "header"
    return "content"


def _classify_cell_intent(cell, table_label):
    """셀 텍스트 → intent 분류."""
    txt = cell["text"]
    if not txt:
        return "empty_input"
    if CHECKBOX_RE.search(txt):
        return "checkbox"
    if PLACEHOLDER_RE.match(txt):
        return "placeholder"
    if EXAMPLE_RE.search(txt):
        return "example"
    if INSTRUCTION_PLACEHOLDER_RE.match(txt):
        return "instruction_placeholder"
    if INSTRUCTION_HINT_RE.match(txt):
        return "instruction"
    if SUBORDINATE_RE.match(txt):
        return "subordinate"
    return "label_or_content"


def _classify_example_rows(tables):
    """fillable-list 표 구조 인식 → example_row + table_terminator 마킹.

    한국 양식 관행: 헤더 + 예시 행 (1~2) + 빈 채움 행 (N) + 생략 행(···)
    이 구조의 표는 예시 행이 *양식 가이드용*. 빌더가 KB 매칭으로 실데이터 교체 또는 비움.
    *구조 신호*만 사용 — 셀 ID·키워드·도메인 식별자 0. yaml 정책 EXAMPLE_ROW_POLICY 만 참조.

    조건 (and):
      1. table.rows >= min_table_rows, cols >= min_table_cols
      2. *헤더 행* 명시적 검출 — 모든 셀 non-empty label_or_content 인 첫 행
      3. terminator(···) 행 ≥ 1 OR 헤더 이후 모든-셀-빈 데이터 행 ≥ min_empty_data_rows
      4. require_terminator=true 면 terminator 도 동시 필수
      5. 헤더 이후 ~ 첫 빈/terminator 행 *이전* 비-empty 행 수 ≤ max_example_rows
      6. require_example_cell_in_candidate=true 면 후보 행에 ≥1 example 셀 필수
    조건 충족 시 헤더 다음 ~ 첫 빈/term 행 *이전* 의 비-empty 행 셀들을 example_row 마킹.
    terminator 행은 별도 table_terminator 마킹.
    """
    if not EXAMPLE_ROW_POLICY.get("enabled", True):
        return
    min_empty = EXAMPLE_ROW_POLICY["min_empty_data_rows"]
    require_term = EXAMPLE_ROW_POLICY["require_terminator"]
    max_ex = EXAMPLE_ROW_POLICY["max_example_rows"]
    min_rows = EXAMPLE_ROW_POLICY["min_table_rows"]
    min_cols = EXAMPLE_ROW_POLICY["min_table_cols"]
    require_ex_cell = EXAMPLE_ROW_POLICY["require_example_cell_in_candidate"]

    for t in tables:
        if t["rows"] < min_rows or t["cols"] < min_cols:
            continue
        cells = t["cells"]
        by_row = {}
        for c in cells:
            by_row.setdefault(c["row"], []).append(c)

        # terminator 행 식별: 행에 셀 1개이며 텍스트가 ellipsis 패턴.
        # (colspan 은 추출기 quirk 로 cols-1 등 다양 — 행 내 단일 셀 + ellipsis 만으로 판정)
        terminator_rows = set()
        for r, rc in by_row.items():
            if len(rc) == 1 and TABLE_ROW_ELLIPSIS_RE.match(rc[0].get("text") or ""):
                terminator_rows.add(r)

        # 헤더 행 명시적 검출: 첫 *모든 셀 non-empty label_or_content* 행.
        # 한국 양식: 헤더 행은 양식 라벨 (label_or_content) 가득. 그 위에 caption 일 수 있음.
        # 헤더 없으면 fillable-list 아님 (자유 텍스트 박스 등) — skip.
        header_row = None
        for r in sorted(by_row):
            rc = by_row[r]
            if not rc:
                continue
            if all((not c.get("is_empty")) and c.get("intent") == "label_or_content" for c in rc):
                header_row = r
                break
        if header_row is None:
            continue

        # 모든-셀-빈 데이터 행 식별 (헤더 이전·terminator 제외)
        all_empty_rows = set()
        for r, rc in by_row.items():
            if r <= header_row or r in terminator_rows:
                continue
            if all(c.get("is_empty") for c in rc):
                all_empty_rows.add(r)

        has_term = len(terminator_rows) >= 1
        has_empty = len(all_empty_rows) >= min_empty
        if require_term:
            is_fillable_list = has_term and has_empty
        else:
            is_fillable_list = has_term or has_empty
        if not is_fillable_list:
            continue

        # 첫 빈/terminator 행 (헤더 이후, 그 이전 비-empty 가 example 후보)
        boundary_rows = {r for r in (all_empty_rows | terminator_rows) if r > header_row}
        if not boundary_rows:
            continue
        first_boundary = min(boundary_rows)
        if first_boundary <= header_row + 1:
            continue  # 헤더 바로 다음이 boundary → example 후보 없음

        # example 후보 행 수집 (header_row+1 ~ first_boundary-1, 비-empty 행만)
        ex_candidates = []
        for r in range(header_row + 1, first_boundary):
            if r in terminator_rows:
                continue
            rc = by_row.get(r, [])
            if not rc or all(c.get("is_empty") for c in rc):
                continue
            ex_candidates.append(r)

        # 너무 많은 example 후보 → 실데이터 표 가능성 (안전 abort)
        if not ex_candidates or len(ex_candidates) > max_ex:
            continue

        # 후보 행 중 ≥1 셀이 intent=example 인지 확인 (내용 신호 검증)
        # 구조 신호(빈 행/terminator) + 내용 신호(example 패턴) 둘 다 요구
        if require_ex_cell:
            has_example_cell = any(
                c.get("intent") == "example"
                for r in ex_candidates
                for c in by_row.get(r, [])
            )
            if not has_example_cell:
                continue

        # 마킹
        for r in ex_candidates:
            for c in by_row.get(r, []):
                c["intent"] = "example_row"
        for r in terminator_rows:
            for c in by_row.get(r, []):
                c["intent"] = "table_terminator"


def walk_section(root, tbl_idx_map):
    """section XML 의 *최상위 hp:p* 만 순회 (셀 안 단락 제외).

    각 hp:p 마다:
      - p_idx (최상위 단락 순서)
      - text (셀 안 텍스트 포함; 별지 헤더가 표 안에 있어도 잡힘)
      - first_tbl_idx (그 paragraph 안 첫 hp:tbl 의 전역 table_idx; 없으면 None)
    """
    p_idx = 0
    for p in root.findall(f"{{{HP_NS}}}p"):
        ptext = "".join(t.text for t in p.iter(f"{{{HP_NS}}}t") if t.text).strip()
        inner_tbls = list(p.iter(f"{{{HP_NS}}}tbl"))
        first_tbl_idx = tbl_idx_map.get(id(inner_tbls[0])) if inner_tbls else None
        yield {"p_idx": p_idx, "text": ptext, "p_el": p, "first_tbl_idx": first_tbl_idx}
        p_idx += 1


def _normalize_label(text):
    """별지 라벨 정규화 — 마커 부분만 추출 (중복 매칭 제거 키)."""
    m = SECTION_MARKER_RE.search(text)
    return re.sub(r"\s+", "", m.group(0)) if m else ""


def _short_label(text):
    """별지 라벨 사람 친화적 추출 — 마커 + 직후 명사구 (최대 30자)."""
    m = SECTION_MARKER_RE.search(text)
    if not m:
        return text[:30]
    start = m.start()
    after = text[m.end():m.end() + 30].strip()
    head = re.split(r"[(\n.]", after, maxsplit=1)[0].strip()
    return (text[start:m.end()] + " " + head).strip()


def detect_sections(walked, total_tables):
    """walked 목록에서 별지 마커 매치 → sections 명세 산출. 동일 라벨 첫 등장만."""
    boundaries = []
    seen = set()
    last_tbl_idx = 0
    for item in walked:
        if item["first_tbl_idx"] is not None:
            last_tbl_idx = item["first_tbl_idx"]
        if not SECTION_MARKER_RE.search(item["text"]):
            continue
        key = _normalize_label(item["text"])
        if key in seen:
            continue
        seen.add(key)
        t_start = item["first_tbl_idx"] if item["first_tbl_idx"] is not None else last_tbl_idx
        boundaries.append({
            "p_idx": item["p_idx"],
            "label": item["text"],
            "table_idx_start": t_start,
        })
    sections = []
    for i, b in enumerate(boundaries):
        next_p = boundaries[i + 1]["p_idx"] if i + 1 < len(boundaries) else None
        next_t = boundaries[i + 1]["table_idx_start"] if i + 1 < len(boundaries) else total_tables
        sections.append({
            "label": _short_label(b["label"]),
            "label_full": b["label"],
            "marker_key": _normalize_label(b["label"]),
            "paragraph_range": [b["p_idx"], next_p],
            "table_idx_range": [b["table_idx_start"], next_t],
        })
    return sections


def _detect_placeholders(walked, sections):
    """walked 단락 목록에서 placeholder 패턴 + 직전 헤더/지침 hint.

    section_header: 직전 *진짜 섹션 헤더* (1-1, 1., 가. 패턴) 또는 직전 비-placeholder 비-지침 텍스트.
    instruction: 직전 ※ 안내 박스 (placeholder 직전 1~2 단락).
    """
    targets = []
    last_section_header = ""
    last_instruction = ""
    last_nonplace = ""
    for item in walked:
        txt = item["text"]
        if not txt:
            continue
        if PLACEHOLDER_RE.match(txt):
            section_label = ""
            for s in sections:
                p0, p1 = s["paragraph_range"]
                if item["p_idx"] >= p0 and (p1 is None or item["p_idx"] < p1):
                    section_label = s["label"]
                    break
            targets.append({
                "id": f"P{item['p_idx']}",
                "type": "paragraph",
                "section_label": section_label,
                "original_text": txt,
                "hints": {
                    "section_header": last_section_header or last_nonplace,
                    "instruction": last_instruction,
                    "section_label": section_label,
                },
            })
            continue
        if INSTRUCTION_HINT_RE.match(txt):
            last_instruction = txt
        elif HEADER_RE.match(txt):
            last_section_header = txt
            last_instruction = ""
            last_nonplace = txt
        else:
            last_nonplace = txt
            last_instruction = ""
    return targets


def analyze_hwpx(hwpx_path: Path):
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with zipfile.ZipFile(str(hwpx_path), "r") as zin:
            zin.extractall(td_path)

        sec_files = sorted((td_path / "Contents").glob("section*.xml"))
        if not sec_files:
            raise RuntimeError("section*.xml 없음")

        all_tables = []
        walked_all = []
        t_offset = 0
        for sf in sec_files:
            tree = etree.parse(str(sf))
            root = tree.getroot()
            tbls_in_sec = list(root.iter(f"{{{HP_NS}}}tbl"))
            tbl_idx_map = {id(t): t_offset + i for i, t in enumerate(tbls_in_sec)}
            for tbl_el in tbls_in_sec:
                tbl = build_table(tbl_idx_map[id(tbl_el)], tbl_el)
                if tbl:
                    all_tables.append(tbl)
            for item in walk_section(root, tbl_idx_map):
                walked_all.append(item)
            t_offset += len(tbls_in_sec)

        sections = detect_sections(walked_all, total_tables=t_offset)

        # 표 후처리: fillable-list 패턴 인식 → example_row + table_terminator 마킹
        # (셀 단위 intent 분류 후, fill_targets 산출 *전* 단계)
        _classify_example_rows(all_tables)

        for t in all_tables:
            label = ""
            for s in sections:
                t0, t1 = s["table_idx_range"]
                if t["idx"] >= t0 and (t1 is None or t["idx"] < t1):
                    label = s["label"]
                    break
            for c in t["cells"]:
                c["section_label"] = label
                if c.get("is_empty"):
                    c["hints"]["section_label"] = label

        for s in sections:
            t0, t1 = s["table_idx_range"]
            cells = [c for t in all_tables if t0 <= t["idx"] < (t1 or 10**9) for c in t["cells"]]
            s["cell_count"] = len(cells)
            s["empty_cell_count"] = sum(1 for c in cells if c.get("is_empty"))

        fill_targets = []
        for t in all_tables:
            for c in t["cells"]:
                intent = c.get("intent", "")
                hints = c.get("hints") or {"left": "", "up": "", "table_label": ""}
                if intent in ("empty_input", "example", "example_row", "checkbox", "instruction_placeholder"):
                    fill_targets.append({
                        "id": c["id"],
                        "type": "cell",
                        "intent": intent,
                        "current_text": c["text"],
                        "section_label": c.get("section_label", ""),
                        "hints": hints,
                    })
                if intent in ("placeholder", "example"):
                    for ip in c.get("inner_ps", []):
                        if ip["intent"] in ("placeholder", "example"):
                            fill_targets.append({
                                "id": f"{c['id']}_P{ip['sub_idx']}",
                                "type": "cell_paragraph",
                                "intent": ip["intent"],
                                "current_text": ip["text"],
                                "section_label": c.get("section_label", ""),
                                "hints": {
                                    "left": hints.get("left", ""),
                                    "up": hints.get("up", ""),
                                    "table_label": hints.get("table_label", ""),
                                    "cell_text": c["text"],
                                },
                            })

        placeholder_targets = _detect_placeholders(walked_all, sections)
        fill_targets.extend(placeholder_targets)

        return {
            "_extracted_from": str(hwpx_path),
            "_purpose": "양식 셀 구조 + 빈 셀 + 별지 분할. proposal-writer 가 본체 별지(rfp_analysis 의 본체_별지) fill_targets 만 채움.",
            "_principle": "양식 절대 안 만짐. 한컴 COM 변환 1회. 본체 별지 산출. 농식품AI/특정 사업 하드코딩 0.",
            "title": "",
            "table_count": len(all_tables),
            "fill_target_count": len(fill_targets),
            "sections": sections,
            "tables": all_tables,
            "fill_targets": fill_targets,
        }


def main():
    if len(sys.argv) < 2:
        print("사용: python scripts/extract_hwpx_form.py <form.hwp|.hwpx> [output.form.yaml]")
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else in_path.with_suffix(".form.yaml")

    with tempfile.TemporaryDirectory() as td:
        td_root = Path(td)
        hwpx_path = ensure_hwpx(str(in_path), td_root)
        data = analyze_hwpx(hwpx_path)

    out_path.write_text(
        yaml.dump(data, Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"저장: {out_path}", file=sys.stderr)
    print(f"  표: {data['table_count']}, 빈 셀: {data['fill_target_count']}, 별지: {len(data['sections'])}", file=sys.stderr)
    for s in data["sections"]:
        print(f"    - {s['label'][:50]} (표 {s['table_idx_range'][0]}~{s['table_idx_range'][1]}, 빈 셀 {s['empty_cell_count']})", file=sys.stderr)


if __name__ == "__main__":
    main()
