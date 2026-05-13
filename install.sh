#!/bin/bash
# DSI 환경 설정 스크립트
#
# 동작:
#   - Python 의존성 설치 (python-docx, python-pptx)
#   - 선택 도구 확인 (pandoc, libreoffice, poppler-utils)
#   - .claude/skills/ 무결성 확인
#   - 결과 보고
#
# 로그: install.log (실행할 때마다 덮어쓰기, 실시간 flush)

set -u  # 미정의 변수 사용 시 종료

LOGFILE="$(dirname "$0")/install.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 로그 덮어쓰기 + 콘솔·파일 동시 출력 (실시간)
: > "$LOGFILE"
exec > >(stdbuf -oL -eL tee "$LOGFILE") 2>&1

log() {
    printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*"
}

fail() {
    log "ERROR: $*"
    exit 1
}

log "=== DSI 환경 설정 시작 ==="
log "작업 디렉토리: $SCRIPT_DIR"
log ""

# ---------- 1. Python 버전 확인 ----------
log "[1/4] Python 버전 확인"
if ! command -v python3 >/dev/null 2>&1; then
    fail "python3 없음. Python 3.10 이상 설치 후 재시도."
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "  python3 = $PY_VER"
log ""

# ---------- 2. 필수 Python 패키지 ----------
log "[2/4] 필수 Python 패키지 설치 (사용자 영역)"
for pkg in python-docx python-pptx; do
    mod_name=$(echo "$pkg" | sed 's/python-//' | tr '-' '_')
    if python3 -c "import $mod_name" 2>/dev/null; then
        log "  ✓ $pkg 이미 설치됨"
    else
        log "  ▶ $pkg 설치 중..."
        if pip3 install --user --quiet "$pkg" 2>&1; then
            log "  ✓ $pkg 설치 완료"
        else
            fail "$pkg 설치 실패"
        fi
    fi
done
log ""

# ---------- 3. 선택 도구 확인 ----------
log "[3/4] 선택 도구 확인 (없어도 동작은 함)"
for tool in pandoc libreoffice pdftoppm; do
    if command -v "$tool" >/dev/null 2>&1; then
        log "  ✓ $tool 사용 가능"
    else
        log "  ⚠ $tool 없음 (선택사항)"
    fi
done
log ""

# ---------- 4. .claude/skills/ 무결성 ----------
log "[4/4] .claude/skills/ 무결성 확인"
REQUIRED_SKILLS=(
    "docx"
    "pptx"
    "korean-public-rfp"
    "dabeeo-profile"
    "proposal-korean-style"
    "ppt-presentation-structure"
)

MISSING=0
for skill in "${REQUIRED_SKILLS[@]}"; do
    if [ -f "$SCRIPT_DIR/.claude/skills/$skill/SKILL.md" ]; then
        log "  ✓ $skill"
    else
        log "  ✗ $skill — SKILL.md 없음"
        MISSING=$((MISSING + 1))
    fi
done
log ""

if [ "$MISSING" -gt 0 ]; then
    fail "$MISSING 개 skill 누락. git pull 또는 재클론 필요."
fi

# ---------- 마무리 ----------
log "=== 설정 완료 ==="
log ""
log "다음 단계:"
log "  1. 이 디렉토리에서 'claude' 실행"
log "  2. 슬래시 명령 '/rfp <파일>' 으로 RFP 처리"
log ""
log "로그 파일: $LOGFILE"

exit 0
