"""HwpObject COM 으로 .hwp/.hwpx → .pdf 변환 (검증·시각확인용).

원칙 (memory/feedback_xml_fill.md):
    한컴 COM 은 *변환 도구*로만 사용. 채움은 XML 결정적 편집.

용법:
    python scripts/hwpx_to_pdf.py <input.hwpx|.hwp> [output.pdf]
    출력 경로 생략 시 입력과 같은 위치에 .pdf 로 저장.
"""
import subprocess
import sys
from pathlib import Path
import win32com.client

# 변환 전 정리할 *오래된* 한컴 좀비 임계 (초). 이전 변환이 안 닫혀 남은 백그라운드
# 인스턴스가 새 COM 변환을 hang 시켜 타임아웃을 유발한다(실측: 13일·7일 된 좀비 →
# 첫 변환 20분 타임아웃, 정리 후 30초). StartTime 이 이 값 초과인 Hwp 만 종료해
# *활성 GUI 편집*(보통 1시간 내 저장)은 보호. 변환은 분 단위라 1시간+ 는 좀비 확정.
STALE_HWP_MAX_AGE_SEC = 3600


def _clear_stale_hwp(max_age_sec: int = STALE_HWP_MAX_AGE_SEC) -> None:
    """변환 전 *오래된* 한컴 좀비 프로세스만 정리 (COM hang 근본 방지).

    StartTime 이 max_age_sec 초과한 Hwp 프로세스만 kill — 방금 시작한 변환 인스턴스나
    활성 GUI 작업은 건드리지 않는다. Windows 전용(한컴 COM 자체가 Windows).
    """
    ps = (
        "$cut=(Get-Date).AddSeconds(-{0});"
        "Get-Process Hwp -ErrorAction SilentlyContinue|"
        "Where-Object{{$_.StartTime -lt $cut}}|"
        "ForEach-Object{{try{{$_.Kill()}}catch{{}};$_.Id}}"
    ).format(int(max_age_sec))
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=30)
        killed = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        if killed:
            print(f"  변환 전 stale 한컴 좀비 정리 (>{max_age_sec}s): PID {killed}")
    except Exception:
        pass  # 정리 실패해도 변환은 시도 (best-effort)


def convert(in_path: str, out_path: str = None, retries: int = 3) -> str:
    _clear_stale_hwp()  # 첫 시도 hang 방지 — 오래된 좀비 선제 정리
    src = Path(in_path).resolve()
    if out_path is None:
        out_path = src.with_suffix(".pdf")
    out_abs = str(Path(out_path).resolve())

    fmt = "HWPX" if src.suffix.lower() == ".hwpx" else "HWP"

    # 한컴 COM 은 연속 호출 시 PDF SaveAs 가 RPC 오류(-2147023170)로 간헐 실패 (비결정성).
    # → 재시도: 실패 시 잔여 프로세스 정리 + 대기 후 재Dispatch (memory/feedback_xml_fill).
    import time
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
