"""form.yaml 의 *사업비 총괄(지원금 합계) 표* 를 RFP 예산 규칙으로 자동 채움.

fill_finance_cells / fill_company_cells 와 *동일 패턴* — 어휘 yaml + 매칭 + 값 계산.
단 사업비는 KB 가 아니라 *RFP 규칙(비율) + 확정 국고 base* 에서 결정적으로 도출.

범위 (1차): 총괄 표 — 국고/자부담/현금/현물 합계. 결정적·완전일반.
  비목별 배분(T62~T64 류)은 2차 (cross-form 검증용 R&D 양식 확보 후).

일반화:
  - 사업·회사·양식 식별자 0. 표번호·좌표 박힘 0.
  - 표 인식 = 헤더 어휘(templates/budget_vocab.yaml). 값 배치 = *다단 헤더 → 레벨별
    데이터 행* 일반 규칙.
  - 비율 = RFP 분석(사업개요.예산) 우선, 없으면 budget_vocab.ratio_defaults.
  - 국고 base·신청유형 = 입력 (비즈니스 결정 — 임의 가정 금지).

용법:
    python scripts/fill_budget_cells.py <form.yaml> <rfp_analysis.yaml> <out_fills.yaml> \
        --gov-eok 20 [--type 타입1]
    # --gov-eok 미지정 시 rfp_analysis 지원유형[type].지원금액_국고 에서 파싱.
"""
import re
import sys
from pathlib import Path
import yaml


def load_vocab(project_root: Path) -> dict:
    return yaml.safe_load((project_root / "templates" / "budget_vocab.yaml").read_text(encoding="utf-8"))


def normalize(text, strip_chars):
    if not text:
        return ""
    s = str(text).strip()
    if strip_chars:
        cls = "".join(re.escape(c) for c in strip_chars)
        s = re.sub(rf"[{cls}]", "", s)
    return re.sub(r"\s+", "", s)


def _first_pct(text):
    """'70%' / '자기부담금 총액의 10% 이상' → 70 / 10."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(text or ""))
    return float(m.group(1)) if m else None


def _first_eok(text):
    """'20억원 내외 (최대 40억원)' → 20.0 (첫 억 단위 수)."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*억", str(text or ""))
    return float(m.group(1)) if m else None


def ratios_from_rfp(rfp: dict, vocab: dict) -> dict:
    """RFP 분석에서 비율 추출. 없으면 ratio_defaults fallback."""
    d = vocab.get("ratio_defaults") or {}
    out = {
        "gov_pct": d.get("gov_pct"), "self_pct": d.get("self_pct"),
        "cash_pct": d.get("cash_pct"), "in_kind_pct": d.get("in_kind_pct"),
    }
    go = (rfp.get("사업개요") or {})
    budget = (go.get("예산") or {})
    if _first_pct(budget.get("국고비율")) is not None:
        out["gov_pct"] = _first_pct(budget.get("국고비율"))
    if _first_pct(budget.get("자기부담금비율")) is not None:
        out["self_pct"] = _first_pct(budget.get("자기부담금비율"))
    sj = (go.get("자기부담금_구성") or {})
    if _first_pct(sj.get("현금")) is not None:
        out["cash_pct"] = _first_pct(sj.get("현금"))
    if _first_pct(sj.get("현물")) is not None:
        out["in_kind_pct"] = _first_pct(sj.get("현물"))
    return out


def gov_base_eok(rfp: dict, sel_type: str, cli_eok: float) -> float:
    """국고 base(억). CLI 우선, 없으면 RFP 지원유형[type].지원금액_국고 파싱."""
    if cli_eok is not None:
        return cli_eok
    go = (rfp.get("사업개요") or {})
    for ent in (go.get("지원유형") or []):
        if sel_type and sel_type.replace(" ", "") in str(ent.get("타입", "")).replace(" ", ""):
            for k, v in ent.items():
                if "국고" in str(k):
                    e = _first_eok(v)
                    if e is not None:
                        return e
    # 신청유형 미지정 시 지원규모.기업당_지원금
    e = _first_eok((go.get("지원규모") or {}).get("기업당_지원금"))
    if e is not None:
        return e
    return None


def _fmt(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")


def compute_totals(gov_eok: float, r: dict) -> dict:
    """국고 base + 비율 → 역할별 금액(억). 결정적."""
    gov = gov_eok
    self_ = gov * (r["self_pct"] / r["gov_pct"])
    cash = self_ * (r["cash_pct"] / 100.0)
    in_kind = self_ * (r["in_kind_pct"] / 100.0)
    total = gov + self_
    return {"total": total, "gov": gov, "self": self_, "cash": cash, "in_kind": in_kind}


def _cells_grid(table):
    """표 → {(r,c): cell}, max_r, max_c. (sub-paragraph _P 변형은 base 셀로 축약)"""
    grid = {}
    for c in (table.get("cells") or []):
        if not isinstance(c, dict):
            continue
        m = re.match(r"^T(\d+)_R(\d+)_C(\d+)$", c.get("id", ""))
        if not m:
            continue
        grid[(int(m.group(2)), int(m.group(3)))] = c
    return grid


def _norm_contains_role(norm_text, role_map):
    """정규화 텍스트에 role_map 의 어떤 key 가 substring 으로 포함되면 그 role 반환."""
    for k, role in role_map.items():
        if k and k in norm_text:
            return role
    return None


def find_detail_tables(tables, vocab):
    """비목별 표 *일반 인식* (배치 라운드의 전제). 셀 id·표번호 하드코딩 0.

    인식 신호 (구조 + 어휘, 양식 무관):
      1. table_terminator(···) 보유 = fillable-list 확정 (extract 가 마킹).
      2. item_roles(인건비/재료비/…) 어휘 매칭 셀 ≥ 2 (여러 비목 나열).
      3. detail_axes.fund(국고/자부담) 어휘 매칭 셀 ≥ 1 (재원 구분 존재).
    → 총괄표(비목 나열 없음)·인건비 상세(비목 1종)·안내표(terminator 없음) 자연 배제.

    반환: 인식된 표 idx 리스트.
    """
    item_roles = vocab.get("item_roles") or {}
    fund = (vocab.get("detail_axes") or {}).get("fund") or {}
    strip = (vocab.get("normalize") or {}).get("strip_chars") or []
    out = []
    for tbl in tables:
        cells = [c for c in (tbl.get("cells") or []) if isinstance(c, dict)]
        if not cells:
            continue
        has_term = any(c.get("intent") == "table_terminator" for c in cells)
        if not has_term:
            continue
        norms = [normalize(c.get("text", ""), strip) for c in cells]
        item_hits = sum(1 for nt in norms if _norm_contains_role(nt, item_roles))
        fund_hits = sum(1 for nt in norms if _norm_contains_role(nt, fund))
        if item_hits >= 2 and fund_hits >= 1:
            out.append({"idx": tbl.get("idx"), "item_hits": item_hits, "fund_hits": fund_hits})
    return out


def find_summary_table(tables, vocab):
    """헤더 어휘로 총괄표 인식. recognize_required 역할이 모두 있어야."""
    st = vocab["summary_table"]
    roles = st["roles"]
    strip = (vocab.get("normalize") or {}).get("strip_chars") or []
    required = set(st.get("recognize_required") or [])
    for tbl in tables:
        present = set()
        for c in (tbl.get("cells") or []):
            if isinstance(c, dict):
                role = roles.get(normalize(c.get("text", ""), strip))
                if role:
                    present.add(role)
        if required and required.issubset(present):
            return tbl
    return None


def build_budget_fills(form, rfp, vocab, gov_eok, sel_type):
    st = vocab["summary_table"]
    roles = st["roles"]
    strip = (vocab.get("normalize") or {}).get("strip_chars") or []
    fmt = st["format"]
    primary = set(st.get("primary_roles") or [])
    sub = set(st.get("sub_roles") or [])

    r = ratios_from_rfp(rfp, vocab)
    amt = compute_totals(gov_eok, r)
    pct = {"total": None, "gov": r["gov_pct"], "self": r["self_pct"],
           "cash": r["cash_pct"], "in_kind": r["in_kind_pct"]}

    tbl = find_summary_table(form.get("tables") or [], vocab)
    if not tbl:
        print("WARN: 총괄(지원금 합계) 표 미검출", file=sys.stderr)
        return [], amt, r
    tidx = tbl.get("idx")
    grid = _cells_grid(tbl)

    # 행별 역할 셀 수집 → 헤더 행(역할 포함) vs 데이터 행 구분.
    rows = sorted({rc[0] for rc in grid})
    role_at = {}   # (r,c) -> role
    header_rows = []
    for rr in rows:
        row_roles = {}
        for (cr, cc), cell in grid.items():
            if cr != rr:
                continue
            role = roles.get(normalize(cell.get("text", ""), strip))
            if role:
                row_roles[cc] = role
        if row_roles:
            header_rows.append(rr)
            for cc, role in row_roles.items():
                role_at[(rr, cc)] = role
    if not header_rows:
        return [], amt, r
    data_rows = [rr for rr in rows if rr > header_rows[-1]]

    # 헤더 레벨 L (header_rows 순서) → 데이터 행 data_rows[L] 의 같은 열에 값.
    fills = []
    for (hr, hc), role in role_at.items():
        level = header_rows.index(hr)
        if level >= len(data_rows):
            continue
        dr = data_rows[level]
        # 값 셀이 grid 에 존재해야 (병합 빈칸 회피)
        if (dr, hc) not in grid:
            continue
        a = amt.get(role)
        if a is None:
            continue
        spec = fmt.get(role, {"num": "{amt}억원"})
        if not isinstance(spec, dict):
            spec = {"num": spec}

        def _expand(tpl):
            s = str(tpl or "").replace("{amt}", _fmt(a))
            if "{pct}" in s and pct.get(role) is not None:
                s = s.replace("{pct}", _fmt(pct[role]))
            return s

        cid = f"T{tidx}_R{dr}_C{hc}"
        src = f"RFP 예산규칙 (국고 {_fmt(amt['gov'])}억 × {role}) — fill_budget_cells"
        # *단락별 fill 사용* (base 셀 fill 회피) — 총괄 셀은 보통 [숫자줄 / 주석줄] 2단락.
        # base 를 쓰면 set_cell_text 가 셀 전체를 1단락으로 합쳐 주석줄이 사라지므로
        # P0(숫자)·P1(주석) 단락을 각각 채운다. 단락 없으면 set_paragraph_text 가 무해 skip.
        fills.append({"id": cid + "_P0", "text": _expand(spec.get("num")), "source": src})
        if "note" in spec:
            fills.append({"id": cid + "_P1", "text": _expand(spec.get("note")), "source": src})
    return fills, amt, r


def main():
    args = sys.argv[1:]
    pos = [a for a in args if not a.startswith("--")]

    # --detect-detail: 비목별 표 *일반 인식* 검증 모드 (form.yaml 1개만 필요).
    # B 배치 라운드의 전제 — 인식 일반성을 cross-form 으로 확인. 배치는 양식 확보 후.
    if "--detect-detail" in args:
        if not pos:
            print("사용: python scripts/fill_budget_cells.py <form.yaml> --detect-detail", file=sys.stderr)
            sys.exit(1)
        form = yaml.safe_load(Path(pos[0]).read_text(encoding="utf-8"))
        vocab = load_vocab(Path(__file__).parent.parent)
        detected = find_detail_tables(form.get("tables") or [], vocab)
        print(f"[detect] 비목별 표 인식: {len(detected)} 개  ({Path(pos[0]).name})", file=sys.stderr)
        for d in detected:
            print(f"  T{d['idx']}: 비목어휘 {d['item_hits']} · 재원어휘 {d['fund_hits']}", file=sys.stderr)
        return

    if len(pos) < 3:
        print("사용: python scripts/fill_budget_cells.py <form.yaml> <rfp_analysis.yaml> "
              "<out_fills.yaml> --gov-eok 20 [--type 타입1]", file=sys.stderr)
        print("  또는: python scripts/fill_budget_cells.py <form.yaml> --detect-detail "
              "(비목별 표 인식 검증)", file=sys.stderr)
        sys.exit(1)
    form_path, rfp_path, out_path = Path(pos[0]), Path(pos[1]), Path(pos[2])
    gov_eok = None
    sel_type = None
    if "--gov-eok" in args:
        gov_eok = float(args[args.index("--gov-eok") + 1])
    if "--type" in args:
        sel_type = args[args.index("--type") + 1]
    project_root = Path(__file__).parent.parent

    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))
    rfp = yaml.safe_load(rfp_path.read_text(encoding="utf-8"))
    vocab = load_vocab(project_root)

    base = gov_base_eok(rfp, sel_type, gov_eok)
    if base is None:
        print("ERROR: 국고 base 미확정 — --gov-eok 지정 필요", file=sys.stderr)
        sys.exit(1)

    fills, amt, r = build_budget_fills(form, rfp, vocab, base, sel_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.dump({"fills": fills}, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    print(f"[OK] 사업비 총괄 fills {len(fills)} 셀 → {out_path}", file=sys.stderr)
    print(f"  비율: 국고 {r['gov_pct']}% / 자부담 {r['self_pct']}% "
          f"(현금 {r['cash_pct']}% / 현물 {r['in_kind_pct']}%)", file=sys.stderr)
    print(f"  국고 {_fmt(amt['gov'])}억 · 자부담 {_fmt(amt['self'])}억 "
          f"(현금 {_fmt(amt['cash'])} / 현물 {_fmt(amt['in_kind'])}) · 총 {_fmt(amt['total'])}억",
          file=sys.stderr)
    for f in fills:
        print(f"  {f['id']}: {f['text']}", file=sys.stderr)


if __name__ == "__main__":
    main()
