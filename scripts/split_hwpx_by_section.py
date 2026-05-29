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


def _section_marker_re():
    """SECTION_MARKER_RE 를 *yaml 정본*에서 가져옴 (extract_hwpx_form 의 로드 메커니즘 재사용).
    별도 yaml 로드 코드 중복 회피 — 단일 정본 보장."""
    try:
        import sys as _sys
        scripts_dir = str(Path(__file__).parent)
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)
        import extract_hwpx_form as _e
        return _e.SECTION_MARKER_RE
    except Exception:
        # fallback: yaml 로드 실패 시 안전 한국 양식 default
        import re as _re
        return _re.compile(r"\[?\s*(별\s*지|붙\s*임|첨\s*부)\s*제?\s*\d+(?:\s*-\s*\d+)?\s*호?\s*\]?", _re.MULTILINE)


def _remove_section_label_box(root):
    """별지 단독 hwpx 의 *시작 별지 라벨 1×1 표* 제거.
    파일명·내용에 이미 별지 식별 정보 있어 시각 박스 불필요. 제거 시 1.기업정보 등
    실제 콘텐츠가 페이지 상단부터 시작 → 페이지 1 빈공간 압축.

    룰 (일반화):
        - 첫 *콘텐츠 단락*이 *1행 1셀 표* 보유
        - 그 표의 텍스트가 SECTION_MARKER_RE (yaml 정본) 매칭
    안 매칭하면 영향 0 — 이미 라벨 박스 없는 별지나 다른 구조 보존.
    HWPX 스키마 상수만 사용.
    """
    sec_re = _section_marker_re()
    for p in list(root.findall(f"{{{HP_NS}}}p")):
        txt = "".join((t.text or "") for t in p.iter(f"{{{HP_NS}}}t")).strip()
        if not txt:
            continue
        tbls = list(p.iter(f"{{{HP_NS}}}tbl"))
        if not tbls:
            return 0  # 콘텐츠는 시작했는데 라벨 박스 아님
        tbl = tbls[0]
        trs = tbl.findall(f"{{{HP_NS}}}tr")
        if len(trs) != 1:
            return 0
        tcs = trs[0].findall(f"{{{HP_NS}}}tc")
        if len(tcs) != 1:
            return 0
        if not sec_re.search(txt):
            return 0
        root.remove(p)
        return 1
    return 0


def _is_content_empty_p(p):
    """top-level hp:p 가 *완전 빈 단락* (텍스트 없음 + 표 없음 + secPr 없음)인지.
    이런 단락은 분할 결과 hwpx 의 *불필요 페이지 자리 차지* 원인이라 정리 대상.
    HWPX 스키마 상수만 사용 — 임의 양식 동일 동작.
    """
    txt = "".join((t.text or "") for t in p.iter(f"{{{HP_NS}}}t")).strip()
    if txt:
        return False
    if list(p.iter(f"{{{HP_NS}}}tbl")):
        return False
    if list(p.iter(f"{{{HP_NS}}}secPr")):
        return False
    return True


def _strip_nonsecpr_runs(p):
    """*secPr 보존 단락* 안의 *secPr 없는 다른 run* 들을 제거.
    split 알고리즘이 keep 한 첫 단락(보통 p0)이 *다른 섹션 헤더*(예: '5 관련양식')의
    텍스트·표 run 도 함께 갖고 들어오는 경우 처리. secPr/ctrl/페이지 설정 run 만 보존.
    HWPX 스키마: run 안에 secPr 있으면 페이지 설정 run, 없으면 콘텐츠 run.
    """
    removed = 0
    for run in list(p.findall(f"{{{HP_NS}}}run")):
        has_secpr = run.find(f"{{{HP_NS}}}secPr") is not None
        if not has_secpr:
            p.remove(run)
            removed += 1
    # 콘텐츠 run 제거 후 linesegarray 도 stale — 한컴 재계산 위해 삭제
    if removed:
        ls = p.find(f"{{{HP_NS}}}linesegarray")
        if ls is not None:
            p.remove(ls)
    return removed


def extract_section(form_hwpx: Path, p_start: int, p_end, out_path: Path):
    """form.hwpx 에서 paragraph_range [p_start, p_end) 만 남긴 .hwpx 생성.
    가드 1: secPr 보존 단락의 *별지 외 콘텐츠* (다른 섹션 헤더 등) run 제거.
    가드 2: 별지 끝의 *trailing 빈 단락* 일괄 제거 (불필요 페이지 방지).
    """
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

        # 가드 1: secPr 보존 단락 (p_start 외 추가 keep 된 첫 단락) 에서 *다른 섹션*
        # 콘텐츠 run 제거 — 별지 단독 결과에 시스템 헤더가 안 보이게.
        if first_p is not None and 0 not in range(p_start, range_end):
            _strip_nonsecpr_runs(first_p)

        # 가드 2: 마지막 콘텐츠 단락 *뒤*의 빈 단락 일괄 제거 (trailing).
        # 통합양식의 별지 영역 *끝*에 패딩 빈 단락 있는 경우 흔함.
        kept_ps = root.findall(f"{{{HP_NS}}}p")
        for p in reversed(kept_ps):
            if _is_content_empty_p(p):
                root.remove(p)
            else:
                break

        # 가드 3: 별지 시작 *라벨 박스* (1×1 표 + SECTION_MARKER 매칭) 제거.
        # 통합양식에서만 의미 있는 시각 헤더. 별지 단독 출력엔 불필요.
        # 임의 양식 동일 동작 — yaml SECTION_MARKER_RE 정본 사용.
        _remove_section_label_box(root)

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
