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
import time
import threading
from pathlib import Path
import win32com.client

# 보안 경고 창 자동 클릭 (백그라운드 스레드)
_auto_click_stop = False

def _auto_click_security_dialogs():
    """보안 경고 창 자동 클릭 - 창 텍스트에 '접근' 포함된 경우만."""
    try:
        import win32gui
        import win32con
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        GetWindowTextW = user32.GetWindowTextW
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        IsWindowVisible = user32.IsWindowVisible
        PostMessageW = user32.PostMessageW
        SetForegroundWindow = user32.SetForegroundWindow
    except ImportError:
        return

    def get_window_text(hwnd):
        length = GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    while not _auto_click_stop:
        try:
            target_hwnd = None

            def enum_callback(hwnd, lParam):
                nonlocal target_hwnd
                if IsWindowVisible(hwnd):
                    title = get_window_text(hwnd)
                    # "접근" 키워드가 포함된 경고창 또는 제목이 정확히 "한글"인 작은 창
                    if "접근" in title or "허용" in title:
                        target_hwnd = hwnd
                        return False  # 찾으면 중단
                return True

            EnumWindows(EnumWindowsProc(enum_callback), 0)

            if target_hwnd:
                SetForegroundWindow(target_hwnd)
                time.sleep(0.05)
                PostMessageW(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                PostMessageW(target_hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                time.sleep(0.1)
        except Exception:
            pass
        time.sleep(0.15)


def start_auto_clicker():
    """자동 클릭 스레드 시작."""
    global _auto_click_stop
    _auto_click_stop = False
    t = threading.Thread(target=_auto_click_security_dialogs, daemon=True)
    t.start()
    return t


def stop_auto_clicker():
    """자동 클릭 스레드 중지."""
    global _auto_click_stop
    _auto_click_stop = True


def safe_filename(label: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "", label)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:80] or "section"


def make_hwp():
    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    # 보안 경고 창 비활성화
    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    # 모든 메시지 박스 자동 확인 (0x00020000 = MB_OK 자동)
    hwp.SetMessageBoxMode(0x00020000)
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
    # PDF도 저장 (실패해도 HWP는 이미 저장됨)
    pdf_path = out_abs.rsplit(".", 1)[0] + ".pdf"
    try:
        hwp.SaveAs(pdf_path, "PDF", "")
    except Exception as e:
        print(f"    PDF 저장 실패: {e}", file=sys.stderr)
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

    # 보안 경고 창 수동 클릭 필요 안내
    print(f"분리: {len(sections)} 별지 (보안창 뜨면 '허용' 클릭)", file=sys.stderr)

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
