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


def convert(in_path: str, out_path: str = None, retries: int = 3) -> str:
    src = Path(in_path).resolve()
    if out_path is None:
        out_path = src.with_suffix(".pdf")
    out_abs = str(Path(out_path).resolve())

    fmt = "HWPX" if src.suffix.lower() == ".hwpx" else "HWP"

    # 한컴 COM 은 연속 호출 시 PDF SaveAs 가 RPC 오류(-2147023170)로 간헐 실패 (비결정성).
    # → 재시도: 실패 시 잔여 프로세스 정리 + 대기 후 재Dispatch (memory/feedback_xml_fill).
    import time
    import subprocess
    last_err = None
    for attempt in range(1, retries + 1):
        hwp = None
        try:
            hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
            # 모든 메시지 박스 자동 확인 (폰트 임베딩 등 대화상자 차단)
            hwp.SetMessageBoxMode(0x00020000)
            if not hwp.Open(str(src), fmt, "forceopen:true"):
                raise RuntimeError(f"열기 실패: {src}")
            saved = hwp.SaveAs(out_abs, "PDF", "")
            try:
                hwp.Quit()
            except Exception:
                pass
            print(f"saved: {out_abs} (success={saved}, attempt={attempt})")
            return out_abs
        except Exception as e:
            last_err = e
            try:
                if hwp is not None:
                    hwp.Quit()
            except Exception:
                pass
            if attempt < retries:
                for im in ("Hwp.exe", "HwpFrame.exe", "Hwp90.exe"):
                    subprocess.run(["taskkill", "/F", "/IM", im],
                                   capture_output=True)
                time.sleep(2)
    raise RuntimeError(f"PDF 변환 {retries}회 실패: {last_err}")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
