"""form.yaml 의 *회사 메타 빈 셀* 을 kb/company/<name>/profile.yaml 데이터로 자동 채움.

fill_finance_cells 와 *동일 패턴* — 라벨 매핑 + lookup. 단, 재무처럼 연도 차원 없음.
양식의 *셀 라벨* (행 또는 직접) → profile_label_map → field → profile.yaml fields[field]
→ 값 채움.

일반화:
  - 회사·RFP·양식 식별자 0개.
  - templates/profile_label_map.yaml 정본 + kb/company/<name>/profile.yaml 정본만.
  - 코드: 알고리즘 (매칭·정규화·hint 추출).

용법:
    python scripts/fill_company_cells.py <form.yaml> <profile.yaml> <out_fills.yaml>

설계 결정:
  - 셀의 *hints* (left·up·table_label) + 셀 본인 텍스트를 *모두 후보 라벨* 로.
    한국 양식 보통 라벨이 *왼쪽 셀* 또는 *위 셀* — extract_hwpx_form 가 hints 채워둠.
  - 매칭 우선순위: exact_labels (정확) > keywords (부분 포함).
  - 빈 셀만 처리. 매칭 없는 셀은 *건너뜀* (proposal-writer 가 처리).
"""
import re
import sys
from pathlib import Path
import yaml


def load_label_map(project_root: Path) -> dict:
    return yaml.safe_load((project_root / "templates" / "profile_label_map.yaml").read_text(encoding="utf-8"))


def normalize(text: str, strip_chars: list = None) -> str:
    """라벨 정규화. yaml strip_chars 정본 사용 (코드 박힘 0).
    fill_finance_cells.normalize 와 동일 정책 — 통일 매커니즘."""
    if not text:
        return ""
    s = str(text).strip()
    if strip_chars:
        cls = "".join(re.escape(c) for c in strip_chars)
        s = re.sub(rf"[{cls}]", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def match_field(label: str, fields_map: dict, strip_chars: list = None) -> str:
    """라벨 → profile field. exact_labels 우선, keywords 부분 매칭."""
    norm = normalize(label, strip_chars)
    if not norm:
        return None
    # exact_labels 매칭 (우선)
    for field, defn in fields_map.items():
        for lbl in (defn.get("exact_labels") or []):
            if normalize(lbl, strip_chars) == norm:
                return field
    # keywords 부분 매칭 (가장 긴 keyword 우선)
    best_field = None
    best_kw_len = 0
    for field, defn in fields_map.items():
        for kw in (defn.get("keywords") or []):
            nkw = normalize(kw, strip_chars)
            if nkw and nkw in norm and len(nkw) > best_kw_len:
                best_kw_len = len(nkw)
                best_field = field
    return best_field


def build_company_fills(form_yaml: Path, profile_yaml: Path, project_root: Path) -> list:
    form = yaml.safe_load(form_yaml.read_text(encoding="utf-8"))
    profile = yaml.safe_load(profile_yaml.read_text(encoding="utf-8"))
    label_map = load_label_map(project_root)
    fields_map = label_map.get("fields") or {}
    strip_chars = (label_map.get("normalize") or {}).get("strip_chars") or []

    profile_values = profile.get("fields") or {}
    if not profile_values:
        print("WARN: profile.yaml 에 fields 없음", file=sys.stderr)
        return []

    tables = form.get("tables") or []
    fills = []
    matched_keys = set()  # (field) — 같은 필드 여러 셀 매칭 시 중복 채움 방지

    # 채움 대상 cell 판정 — 빈 셀 + example intent.
    # 예시 텍스트(00법인·홍길동·0000.00.00)도 *값 자리* 이므로 KB값으로 교체.
    # 임의 양식의 예시 표기를 *override* 하는 일반 룰.
    def _is_fillable(c):
        if c.get("is_empty"):
            return True
        if c.get("intent") == "example":
            return True
        return False

    for tbl in tables:
        if not isinstance(tbl, dict):
            continue
        cells = tbl.get("cells") or []
        # 표 안 cell index — hint 보강용 (행 라벨 lookup 등)
        cell_by_pos = {}
        for c in cells:
            if isinstance(c, dict):
                cid_m = re.match(r"^T(\d+)_R(\d+)_C(\d+)$", c.get("id", ""))
                if cid_m:
                    cell_by_pos[(int(cid_m.group(2)), int(cid_m.group(3)))] = c

        for c in cells:
            if not isinstance(c, dict):
                continue
            cid = c.get("id", "")
            if not cid:
                continue
            # 후보 라벨: hints.left (우선) → hints.up → 셀 자체 text → 같은 행 더 왼쪽 셀
            hints = c.get("hints") or {}
            candidates = []
            if hints.get("left"):
                candidates.append(hints["left"])
            if hints.get("up"):
                candidates.append(hints["up"])
            cell_text = (c.get("text") or "").strip()
            if cell_text:
                candidates.append(cell_text)
            # 매칭 시도
            field = None
            for lbl in candidates:
                field = match_field(lbl, fields_map, strip_chars)
                if field:
                    break
            if not field:
                continue
            # 셀이 *채움 가능* (빈 또는 example) 여부 + *맥락 기반 example 보강*:
            # 라벨이 메타 필드 매칭이면 *그 셀은 의미상 *값 자리** — 예시 텍스트 있어도
            # 채움 대상 (label_or_content 분류된 '홍 길 동' 등). 매칭이 *cell_text 자체*
            # 면 그건 라벨 셀이므로 채움 X.
            label_came_from = "cell_text" if (cell_text and match_field(cell_text, fields_map, strip_chars) == field) else "hint"
            if label_came_from == "cell_text":
                # 값 자리 아닌 라벨 셀 (예: "주관기업명")
                continue
            if not _is_fillable(c) and label_came_from == "hint":
                # 라벨 매칭 + 빈 아님 + example 아님 = *맥락상 예시일 가능성*
                # → fill 대상으로 확장 (override 허용). 실제 라벨 텍스트가 들어있다면
                # 위 cell_text 매칭에서 걸렸을 것.
                pass  # 진행
            value = profile_values.get(field)
            if value is None or value == "":
                continue
            # 같은 field 한 셀에만 (첫 매칭 셀만 채움)
            key = (cid.split("_R")[0], field)
            if key in matched_keys:
                continue
            matched_keys.add(key)
            fills.append({
                "id": cid,
                "text": str(value),
                "source": f"kb profile.yaml ({field})",
            })

    return fills


def main():
    if len(sys.argv) < 4:
        print("사용: python scripts/fill_company_cells.py <form.yaml> <profile.yaml> <out_fills.yaml>", file=sys.stderr)
        sys.exit(1)
    form_path = Path(sys.argv[1])
    profile_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])
    project_root = Path(__file__).parent.parent

    fills = build_company_fills(form_path, profile_path, project_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.dump({"fills": fills}, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"[OK] fills 생성: {len(fills)} 셀 → {out_path}", file=sys.stderr)
    for f in fills[:15]:
        print(f"  {f['id']}: {f['text'][:40]!r} ({f['source']})", file=sys.stderr)


if __name__ == "__main__":
    main()
