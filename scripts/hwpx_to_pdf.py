"""HwpObject COM 으로 .hwp/.hwpx → .pdf 변환 (검증·시각확인용).

원칙 (memory/feedback_xml_fill.md):
    한컴 COM 은 *변환 도구*로만 사용. 채움은 XML 결정적 편집.

용법:
    python scripts/hwpx_to_pdf.py <input.hwpx|.hwp> [output.pdf]
    출력 경로 생략 시 입력과 같은 위치에 .pdf 로 저장.
"""
import sys
from pathlib import Path
import win32com.client


def convert(in_path: str, out_path: str = None) -> str:
    src = Path(in_path).resolve()
    if out_path is None:
        out_path = src.with_suffix(".pdf")
    out_abs = str(Path(out_path).resolve())

    fmt = "HWPX" if src.suffix.lower() == ".hwpx" else "HWP"

    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    # 보안 경고 창 비활성화
    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    # 모든 메시지 박스 자동 확인 (PDF 저장 시 폰트 임베딩 등 대화상자 차단 → RPC 실패 방지)
    hwp.SetMessageBoxMode(0x00020000)
    if not hwp.Open(str(src), fmt, "forceopen:true"):
        raise RuntimeError(f"열기 실패: {src}")
    saved = hwp.SaveAs(out_abs, "PDF", "")
    hwp.Quit()
    print(f"saved: {out_abs} (success={saved})")
    return out_abs


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
