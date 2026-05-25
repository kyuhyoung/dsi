"""HwpObject COM 으로 .hwp → .hwpx 변환 (1회 사용).

원칙 (memory/feedback_xml_fill.md):
    한컴 COM 은 *변환 도구*로만 1회 사용. 채움은 XML 결정적 편집.

용법:
    python scripts/hwp_to_hwpx.py <input.hwp> <output.hwpx>
"""
import sys
from pathlib import Path
import win32com.client


def convert(in_path: str, out_path: str):
    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    for mod in ("FilePathCheckDLL", "FilePathChecker"):
        try:
            hwp.RegisterModule("FilePathCheckerModule", mod)
        except Exception:
            pass
    if not hwp.Open(str(Path(in_path).resolve()), "HWP", "forceopen:true"):
        raise RuntimeError(f"열기 실패: {in_path}")
    out_abs = str(Path(out_path).resolve())
    saved = hwp.SaveAs(out_abs, "HWPX", "")
    hwp.Quit()
    print(f"saved: {out_abs} (success={saved})")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
