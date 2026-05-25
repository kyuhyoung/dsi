#!/usr/bin/env python3
"""HWP 양식 + fills.yaml → 채워진 .hwp.

원칙 (memory/feedback_form_principle.md):
    양식은 절대 만지지 않는다. 빈 셀에 텍스트만 박는다.
    → 양식 visual·border·색·서식 일체 미변경. HwpObject COM 이 텍스트만 삽입.

용법:
    python scripts/fill_hwp_form.py <form.hwp> <fills.yaml> <output.hwp>

fills.yaml 스키마 (proposal-writer 산출):
    fills:
      - id: T{table_idx}_R{row}_C{col}
        text: "채울 텍스트"
      - ...

일반화:
    - 양식 종류 무관 (.hwp). 표·셀 식별은 좌표(idx, row, col) 기반.
    - fills.yaml 의 id 형식만 맞으면 동작. 도메인·사업명·회사명 무관.
    - 멀티라인 텍스트 지원 (text 안의 \\n → InsertText 분할).
"""
import re
import sys
import yaml
from pathlib import Path
import win32com.client


CELL_ID_RE = re.compile(r"^T(\d+)_R(\d+)_C(\d+)$")


def parse_cell_id(cell_id: str):
    m = CELL_ID_RE.match(cell_id)
    if not m:
        raise ValueError(f"잘못된 cell id 형식: {cell_id!r} (T{{n}}_R{{r}}_C{{c}} 기대)")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def make_hwp():
    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    for mod in ("FilePathCheckDLL", "FilePathChecker"):
        try:
            hwp.RegisterModule("FilePathCheckerModule", mod)
        except Exception:
            pass
    return hwp


def find_table_ctrl(hwp, target_idx: int):
    ctrl = hwp.HeadCtrl
    found = -1
    while ctrl:
        if ctrl.CtrlID == "tbl":
            found += 1
            if found == target_idx:
                return ctrl
        ctrl = ctrl.Next
    return None


def goto_cell(hwp, table_idx: int, row: int, col: int) -> bool:
    hwp.Run("Cancel")
    ctrl = find_table_ctrl(hwp, table_idx)
    if ctrl is None:
        return False
    hwp.SetPosBySet(ctrl.GetAnchorPos(0))
    hwp.HAction.Run("MoveDown")
    hwp.HAction.Run("TableColBegin")
    for _ in range(row):
        hwp.HAction.Run("TableLowerCell")
    for _ in range(col):
        hwp.HAction.Run("TableRightCell")
    return True


def insert_text(hwp, text: str):
    """multi-line 지원. \n 만나면 줄바꿈 (BreakPara)."""
    parts = text.split("\n")
    for i, part in enumerate(parts):
        if i > 0:
            hwp.Run("BreakPara")
        if part:
            hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
            hwp.HParameterSet.HInsertText.Text = part
            hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)


def fill_form(form_path: str, fills_path: str, out_path: str):
    fills_data = yaml.safe_load(Path(fills_path).read_text(encoding="utf-8"))
    fills = fills_data.get("fills", [])
    if not fills:
        print("WARN: fills 비어있음", file=sys.stderr)

    hwp = make_hwp()
    opened = hwp.Open(str(Path(form_path).resolve()), "HWP", "forceopen:true")
    if not opened:
        raise RuntimeError(f"양식 열기 실패: {form_path}")

    filled = 0
    failed = []
    for entry in fills:
        cid = entry.get("id", "")
        text = entry.get("text", "")
        if not cid or text == "":
            continue
        try:
            t, r, c = parse_cell_id(cid)
        except ValueError as e:
            failed.append((cid, str(e)))
            continue
        if not goto_cell(hwp, t, r, c):
            failed.append((cid, f"표 {t} 못 찾음"))
            continue
        insert_text(hwp, str(text))
        filled += 1

    hwp.SaveAs(str(Path(out_path).resolve()), "HWP", "")
    hwp.Quit()

    print(f"채움 완료: {filled}/{len(fills)} 셀", file=sys.stderr)
    if failed:
        print(f"실패 {len(failed)}:", file=sys.stderr)
        for cid, err in failed[:10]:
            print(f"  {cid}: {err}", file=sys.stderr)
        if len(failed) > 10:
            print(f"  ... +{len(failed) - 10}", file=sys.stderr)


def main():
    if len(sys.argv) < 4:
        print("사용: python scripts/fill_hwp_form.py <form.hwp> <fills.yaml> <output.hwp>")
        sys.exit(1)
    fill_form(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
