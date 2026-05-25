#!/usr/bin/env python3
"""한컴 매크로로 통합 양식 → 별지별 .hwp 분리.

원칙 (memory):
    - 임의 양식 동작 — form.yaml 의 sections.paragraph_range 그대로 활용
    - 산출물 output 폴더 (Temp 금지)
    - 한컴 COM 사용 — XML 분할이 한컴 검증 실패하므로 우회

용법:
    python scripts/split_hwp_by_section_macro.py <form.hwp|.hwpx> <form.yaml> <output_dir>

알고리즘 (각 별지):
    1. 한컴으로 통합 양식 열기
    2. paragraph_range 시작 위치로 카서 이동 (MovePos)
    3. selection 시작 (Block on)
    4. paragraph_range 끝 위치로 이동 (selection 확장)
    5. Copy
    6. FileNew (새 빈 hwp 문서)
    7. Paste
    8. SaveAs(별지N.hwp)
    9. 닫고 다음 별지 — 통합 양식 다시 열기 (selection state reset)
"""
import re
import sys
import yaml
from pathlib import Path
import win32com.client


def safe_filename(label: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "", label)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:80] or "section"


def make_hwp():
    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    for mod in ("FilePathCheckDLL", "FilePathChecker"):
        try:
            hwp.RegisterModule("FilePathCheckerModule", mod)
        except Exception:
            pass
    try:
        hwp.SetMessageBoxMode(0x00000020)
    except Exception:
        pass
    return hwp


def split_one(src_hwp: str, p_start: int, p_end, out_path: str):
    """통합 양식 src_hwp 에서 paragraph [p_start, p_end) 만 잘라 out_path 로 저장."""
    hwp = make_hwp()
    fmt = "HWPX" if str(src_hwp).lower().endswith(".hwpx") else "HWP"
    if not hwp.Open(str(Path(src_hwp).resolve()), fmt, "forceopen:true"):
        raise RuntimeError(f"열기 실패: {src_hwp}")

    hwp.MovePos(0, p_start, 0)
    hwp.Run("Select")
    end_p = (p_end - 1) if p_end is not None else None
    if end_p is None:
        hwp.Run("MoveDocEnd")
    else:
        hwp.MovePos(0, end_p, 0)
        hwp.Run("MoveSelLineEnd")
    hwp.Run("Copy")

    hwp.Run("FileNew")
    hwp.Run("Paste")

    out_abs = str(Path(out_path).resolve())
    hwp.SaveAs(out_abs, "HWP", "")
    hwp.Quit()


def main():
    if len(sys.argv) < 4:
        print("사용: python scripts/split_hwp_by_section_macro.py <form.hwp|.hwpx> <form.yaml> <output_dir>")
        sys.exit(1)
    src = Path(sys.argv[1])
    fy = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    data = yaml.safe_load(fy.read_text(encoding="utf-8"))
    sections = data.get("sections", [])
    if not sections:
        print("ERR: sections 비어있음", file=sys.stderr)
        sys.exit(1)

    print(f"분리: {len(sections)} 별지", file=sys.stderr)
    for i, s in enumerate(sections):
        p_start, p_end = s["paragraph_range"]
        fname = f"{i+1:02d}_{safe_filename(s['label'])}.hwp"
        out_path = out_dir / fname
        try:
            split_one(str(src), p_start, p_end, str(out_path))
            size = out_path.stat().st_size if out_path.exists() else 0
            print(f"  OK {fname} ({size:,} B) p{p_start}~{p_end}", file=sys.stderr)
        except Exception as e:
            print(f"  ERR {fname}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
