"""form.yaml 의 *재무 표 빈셀*을 finance.yaml 데이터로 자동 채움.

일반화:
  - 회사·RFP·양식 식별자 0개.
  - 표 인식: 빈셀의 *행 라벨* + *열 라벨* 컨텍스트로 (field, year) 식별.
    행 라벨 = 같은 행의 첫 텍스트 셀.
    열 라벨 = 같은 표 첫 텍스트 행에서 같은(또는 합쳐진) col 의 텍스트 셀.
  - 매핑: templates/finance_label_map.yaml 의 keywords → field.
  - 단위: 셀·행 라벨에서 단위 표기 (백만원/억원/천원/원) 추출.
          미표기 시 unit_default (한국 RFP 관행: 백만원).
  - 데이터 없으면 fill 안 생성 → 빈 셀 그대로 (빌더가 '확인 필요' 표기 가능).

용법:
    python scripts/fill_finance_cells.py <form.yaml> <finance.yaml> <out_fills.yaml>

설계 결정:
  - *별지 한정 옵션*: --section "[별지 제2-2호]" 로 특정 별지의 셀만 처리.
    안 주면 *전체 양식*의 모든 재무 표 자동 검색.
  - *행 라벨 매칭*: keyword 부분 포함 (대소문자·공백 무시).
    경합 시 *합계/총계* 행 우선 (extract_finance 와 동일).
  - *fills 형식*: fill_hwpx_form.py 가 기대하는 {id, text, source, operation} 스키마.

이 스크립트는 *fills 만 생성*. 실제 XML 채움은 fill_hwpx_form.py 가 담당.
"""
import re
import sys
from pathlib import Path
import yaml


YEAR_LABEL_RE = re.compile(r"(\d{4})\s*년?")
# 단위 검출 — *명시 표기*만 (안 그러면 '증명원'·'본 사업원' 같은 일반어 '원'이 잘못 매칭).
# 우선순위: 괄호 안 단위 > '단위: X' 표기 > 단독 라벨 셀 ('백만원' 만 있는 짧은 셀)
UNIT_PAREN_RE = re.compile(r"[\(（\[]\s*(백만원|억원|천원|원)\s*[\)）\]]")
UNIT_LABEL_RE = re.compile(r"단위\s*[:：\-]\s*(백만원|억원|천원|원)")
UNIT_STANDALONE_RE = re.compile(r"^\s*(백만원|억원|천원|원)\s*$")


def load_label_map(project_root: Path) -> dict:
    return yaml.safe_load((project_root / "templates" / "finance_label_map.yaml").read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    if not text:
        return ""
    s = text.strip()
    s = re.sub(r"[（）()\[\]※\*:,]", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def match_field(row_label: str, fields: dict) -> str:
    """행 라벨 → finance 필드명. 매칭 없으면 None."""
    norm = normalize(row_label)
    if not norm:
        return None
    best_field = None
    best_score = -1
    for field, defn in fields.items():
        for kw in defn.get("keywords") or []:
            nk = normalize(kw)
            if nk and nk in norm:
                score = 10 + len(nk)  # 긴 keyword 우선 (전체 일치 가까움)
                if norm == nk:
                    score += 50
                if score > best_score:
                    best_score = score
                    best_field = field
    return best_field


def extract_year(label: str) -> str:
    """라벨에서 4자리 연도 추출 ('2024년' → '2024'). 못 찾으면 None."""
    if not label:
        return None
    m = YEAR_LABEL_RE.search(str(label))
    return m.group(1) if m else None


def extract_unit_divisor(label_texts: list, unit_default: dict) -> tuple:
    """라벨들에서 *명시 단위 표기* 찾기. 못 찾으면 default.
    (unit_str, divisor) 반환. 일반어 '원' 오매칭 방지: 괄호·'단위:' 형식만 허용.
    """
    divisors = {"백만원": 1000000, "억원": 100000000, "천원": 1000, "원": 1}
    # 우선순위: 괄호 > 단위: > 단독
    for txt in label_texts:
        if not txt:
            continue
        s = str(txt)
        for rx in (UNIT_PAREN_RE, UNIT_LABEL_RE):
            m = rx.search(s)
            if m:
                u = m.group(1)
                return u, divisors[u]
        m = UNIT_STANDALONE_RE.match(s)
        if m:
            u = m.group(1)
            return u, divisors[u]
    return unit_default.get("pattern", "백만원"), int(unit_default.get("divisor", 1000000))


def find_finance_tables(form: dict, fields: dict, target_section_label: str = None) -> list:
    """form.yaml 의 tables 중 재무 표만 식별.
    재무 표 = *연도 헤더* (FY/2023/2024/2025 등) + *재무 키워드 행 라벨* 1개 이상.
    재무 키워드는 finance_label_map.yaml 의 모든 keywords 합집합 — yaml 정본.
    """
    # 모든 필드의 keywords 합집합 (yaml 정본)
    all_keywords = set()
    for field_def in fields.values():
        for kw in (field_def.get("keywords") or []):
            if isinstance(kw, str) and kw.strip():
                all_keywords.add(kw.strip())
    # exact_labels 도 포함
    for field_def in fields.values():
        for lbl in (field_def.get("exact_labels") or []):
            if isinstance(lbl, str) and lbl.strip():
                all_keywords.add(lbl.strip())

    tables = form.get("tables") or []
    found = []
    for t in tables:
        if not isinstance(t, dict):
            continue
        cells = t.get("cells") or []
        if not cells:
            continue
        # 셀의 텍스트 모음 검사 — 연도 헤더 + 재무 키워드 행 있어야
        all_texts = [(c.get("text") or "").strip() for c in cells if isinstance(c, dict)]
        years_seen = any(YEAR_LABEL_RE.search(t) for t in all_texts)
        finance_kw_seen = any(
            any(kw in t for kw in all_keywords) for t in all_texts
        )
        if years_seen and finance_kw_seen:
            # section filter
            if target_section_label:
                sec = t.get("section_label", "") or ""
                # cell-level section_label 도 확인 (form.yaml 구조에 따라)
                if target_section_label not in sec:
                    # cell의 section_label도 확인
                    any_match = any(
                        target_section_label in (c.get("section_label", "") or "")
                        for c in cells if isinstance(c, dict)
                    )
                    if not any_match:
                        continue
            found.append(t)
    return found


def build_row_col_labels(cells: list) -> tuple:
    """셀 리스트에서 *행 라벨 dict* + *열 라벨 dict* 구축.
    row_labels: {row_idx: 첫 텍스트 셀의 text}
    col_labels: {col_idx: 같은 표 첫 텍스트 행에서 그 col 의 text} — 인접 col 도 매핑 (합쳐진 헤더 셀 처리).
    """
    # cell id 파싱 — T<n>_R<r>_C<c>
    parsed = []
    for c in cells:
        if not isinstance(c, dict):
            continue
        cid = c.get("id", "")
        m = re.match(r"^T(\d+)_R(\d+)_C(\d+)$", cid)
        if not m:
            continue
        r = int(m.group(2))
        col = int(m.group(3))
        txt = (c.get("text") or "").strip()
        is_empty = bool(c.get("is_empty")) or bool(c.get("fill_target"))
        parsed.append({"id": cid, "r": r, "c": col, "text": txt, "is_empty": is_empty})

    if not parsed:
        return {}, {}, []

    # 행 라벨: 각 행 최저 col 의 비빈 text
    row_labels = {}
    for p in sorted(parsed, key=lambda x: (x["r"], x["c"])):
        if p["text"] and p["r"] not in row_labels:
            row_labels[p["r"]] = p["text"]

    # 헤더 행 찾기 — 가장 작은 r 중 연도가 들어있는 행
    header_rs = sorted({p["r"] for p in parsed if YEAR_LABEL_RE.search(p["text"])})
    header_r = header_rs[0] if header_rs else None

    # 열 라벨: header_r 의 텍스트 셀 → col_label. 인접 col 채움 (다음 텍스트 셀 직전까지 같은 라벨).
    col_labels = {}
    if header_r is not None:
        header_cells = sorted([p for p in parsed if p["r"] == header_r and p["text"]], key=lambda x: x["c"])
        # 모든 col 에 라벨 — 다음 헤더 col 직전까지 같은 라벨 전파
        all_cols = sorted({p["c"] for p in parsed})
        cur_label = None
        for col in all_cols:
            for h in header_cells:
                if h["c"] == col:
                    cur_label = h["text"]
                    break
            if cur_label:
                col_labels[col] = cur_label

    return row_labels, col_labels, parsed


def build_finance_fills(form_yaml: Path, finance_yaml: Path, project_root: Path,
                        target_section_label: str = None) -> list:
    form = yaml.safe_load(form_yaml.read_text(encoding="utf-8"))
    finance = yaml.safe_load(finance_yaml.read_text(encoding="utf-8"))
    label_map = load_label_map(project_root)
    fields = label_map.get("fields") or {}
    unit_default = label_map.get("unit_default") or {"pattern": "백만원", "divisor": 1000000}

    records = finance.get("records") or {}
    if not records:
        print("WARN: finance.yaml 에 records 없음", file=sys.stderr)
        return []

    fin_tables = find_finance_tables(form, fields, target_section_label)
    print(f"재무 표 검출: {len(fin_tables)} 개", file=sys.stderr)

    fills = []
    for tbl in fin_tables:
        cells = tbl.get("cells") or []
        row_labels, col_labels, parsed = build_row_col_labels(cells)
        # 표 전체 텍스트에서 단위 추출
        all_label_texts = list(row_labels.values()) + list(col_labels.values())
        # 표 외부 안내문도 가능 — section 의 caption / table_label
        all_label_texts.append(tbl.get("table_label", "") or "")
        unit_str, divisor = extract_unit_divisor(all_label_texts, unit_default)

        # 빈셀 순회
        for p in parsed:
            if not p["is_empty"]:
                continue
            row_lbl = row_labels.get(p["r"], "")
            col_lbl = col_labels.get(p["c"], "")
            # 셀 자신의 단위 우선
            cell_unit, cell_divisor = extract_unit_divisor([row_lbl, col_lbl], None) if False else (unit_str, divisor)
            # row 라벨 → field
            field = match_field(row_lbl, fields)
            if not field:
                continue
            # col 라벨 → year
            year = extract_year(col_lbl)
            if not year:
                # 가로 형식이 아닌 경우 (행에 연도, 열에 항목) — TODO 추후
                continue
            rec = records.get(year) or records.get(str(year))
            if not rec:
                continue
            value = rec.get(field)
            if value is None:
                continue
            # 단위 변환
            converted = int(round(value / cell_divisor))
            text = f"{converted:,}"
            fills.append({
                "id": p["id"],
                "text": text,
                "source": f"kb finance.yaml ({year}, {field}, ÷{cell_divisor})",
            })

    return fills


def main():
    if len(sys.argv) < 4:
        print("사용: python scripts/fill_finance_cells.py <form.yaml> <finance.yaml> <out_fills.yaml> [--section LABEL]", file=sys.stderr)
        sys.exit(1)
    form_path = Path(sys.argv[1])
    finance_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])
    project_root = Path(__file__).parent.parent

    target = None
    if "--section" in sys.argv:
        i = sys.argv.index("--section")
        if i + 1 < len(sys.argv):
            target = sys.argv[i + 1]

    fills = build_finance_fills(form_path, finance_path, project_root, target)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # fill_hwpx_form.py 가 기대하는 {fills: [...]} 형식 (top-level list 아님)
    out_path.write_text(
        yaml.dump({"fills": fills}, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"[OK] fills 생성: {len(fills)} 셀 → {out_path}", file=sys.stderr)
    for f in fills[:10]:
        print(f"  {f['id']}: {f['text']} ({f['source']})", file=sys.stderr)


if __name__ == "__main__":
    main()
