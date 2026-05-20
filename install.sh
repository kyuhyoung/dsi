#!/bin/bash
# DSI 환경 설정 스크립트 v2
#
# 동작:
#   - Python 3.10+ 확인 + requirements.txt 일괄 설치
#   - 선택 도구 점검 (Node.js·mmdc·LibreOffice·pandoc·poppler)
#   - .claude/skills/ 무결성 확인
#   - templates/ 자동 sync 시범 실행
#   - 결과 요약 + 다음 단계 안내
#
# 로그: install.log (실행할 때마다 덮어쓰기, 실시간 flush)

set -u

LOGFILE="$(dirname "$0")/install.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

: > "$LOGFILE"
exec > >(stdbuf -oL -eL tee "$LOGFILE") 2>&1

log() {
    printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*"
}

fail() {
    log "오류: $*"
    log ""
    log "전체 로그: $LOGFILE"
    exit 1
}

OK_COUNT=0
WARN_COUNT=0

ok() {
    log "  ✓ $*"
    OK_COUNT=$((OK_COUNT + 1))
}

warn() {
    log "  ⚠ $* (선택 사항)"
    WARN_COUNT=$((WARN_COUNT + 1))
}

log "=== DSI 환경 설정 시작 ==="
log "작업 디렉토리: $SCRIPT_DIR"
log ""

# ─────────────────────────────────────────
# 1. Python 3.10+
# ─────────────────────────────────────────
log "[1/6] Python 점검"
if ! command -v python3 >/dev/null 2>&1; then
    fail "python3 없음. Python 3.10 이상 설치 후 재시도."
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    fail "Python $PY_VER 감지됨. 3.10 이상이 필요합니다."
fi
ok "python3 $PY_VER"
log ""

# ─────────────────────────────────────────
# 2. Python 의존성 (requirements.txt)
# ─────────────────────────────────────────
log "[2/6] Python 의존성 설치 (requirements.txt)"
if [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
    fail "requirements.txt 없음. git pull 또는 재클론 필요."
fi
if pip3 install --user --quiet -r "$SCRIPT_DIR/requirements.txt" 2>&1; then
    ok "requirements.txt 설치 완료"
else
    fail "requirements.txt 설치 실패. 수동 시도: pip3 install --user -r requirements.txt"
fi
log ""

# ─────────────────────────────────────────
# 3. Node.js + Mermaid CLI (선택)
# ─────────────────────────────────────────
log "[3/6] Mermaid CLI (선택, 다이어그램 자동 변환용)"
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    NODE_VER=$(node --version)
    ok "Node.js $NODE_VER"
    if [ -f "$SCRIPT_DIR/package.json" ]; then
        if [ ! -f "$SCRIPT_DIR/node_modules/.bin/mmdc" ]; then
            log "  ▶ mermaid-cli 설치 중..."
            (cd "$SCRIPT_DIR" && npm install --silent 2>&1) || warn "npm install 실패. Mermaid 미사용."
        fi
        if [ -f "$SCRIPT_DIR/node_modules/.bin/mmdc" ]; then
            ok "mmdc 사용 가능"
        else
            warn "mmdc 미설치"
        fi
    else
        warn "package.json 없음 (mermaid 미사용 환경)"
    fi
else
    warn "Node.js 없음. type:mermaid yaml 미사용이면 무시 OK. (Ubuntu: sudo apt install nodejs npm)"
fi
log ""

# ─────────────────────────────────────────
# 4. LibreOffice (PDF 변환용, 선택)
# ─────────────────────────────────────────
log "[4/6] LibreOffice (선택, .pptx → .pdf 변환용)"
SOFFICE=""
if command -v soffice >/dev/null 2>&1; then
    SOFFICE="soffice"
elif command -v libreoffice >/dev/null 2>&1; then
    SOFFICE="libreoffice"
elif [ -f "/mnt/c/Program Files/LibreOffice/program/soffice.exe" ]; then
    SOFFICE="/mnt/c/Program Files/LibreOffice/program/soffice.exe"
elif [ -f "/mnt/c/Program Files (x86)/LibreOffice/program/soffice.exe" ]; then
    SOFFICE="/mnt/c/Program Files (x86)/LibreOffice/program/soffice.exe"
fi
if [ -n "$SOFFICE" ]; then
    ok "LibreOffice 발견: $SOFFICE"
else
    warn "LibreOffice 없음. PDF 변환 안 됨 (.pptx 자체는 정상 생성). 설치: https://www.libreoffice.org/"
fi
log ""

# ─────────────────────────────────────────
# 5. 기타 선택 도구
# ─────────────────────────────────────────
log "[5/6] 기타 선택 도구"
if command -v pandoc >/dev/null 2>&1; then ok "pandoc"; else warn "pandoc 없음 (Word 텍스트 추출 시 필요)"; fi
if command -v pdftoppm >/dev/null 2>&1; then ok "pdftoppm"; else warn "pdftoppm 없음 (PDF→이미지 변환 시 필요. Ubuntu: sudo apt install poppler-utils)"; fi
log ""

# ─────────────────────────────────────────
# 6. .claude/skills/ 무결성 + templates/ sync
# ─────────────────────────────────────────
log "[6/6] .claude/skills/ 무결성 확인"
REQUIRED_SKILLS=(
    "docx" "pptx" "korean-public-rfp"
    "dabeeo-profile" "proposal-korean-style" "ppt-presentation-structure"
)
MISSING=0
for skill in "${REQUIRED_SKILLS[@]}"; do
    if [ -f "$SCRIPT_DIR/.claude/skills/$skill/SKILL.md" ]; then
        ok "$skill"
    else
        log "  ✗ $skill — SKILL.md 없음"
        MISSING=$((MISSING + 1))
    fi
done
if [ "$MISSING" -gt 0 ]; then
    fail "$MISSING 개 skill 누락. git pull 또는 재클론 필요."
fi

log ""
log "      templates/ 등록 안내"
TEMPLATE_COUNT=$(find "$SCRIPT_DIR/templates" -maxdepth 1 -name "*.pptx" 2>/dev/null | wc -l)
STYLE_COUNT=$(find "$SCRIPT_DIR/templates" -maxdepth 1 -name "*.style.yaml" 2>/dev/null | wc -l)
if [ "$TEMPLATE_COUNT" -gt 0 ]; then
    ok "templates/ 발견: $TEMPLATE_COUNT 개 .pptx, $STYLE_COUNT 개 style.yaml"
    log "      신규/변경된 template은 Claude Code에서 /onboard-template 실행"
else
    log "      ℹ templates/ 비어있음. 회사 .pptx를 떨궈 넣고 /onboard-template 실행"
fi
log ""

# ─────────────────────────────────────────
# 마무리
# ─────────────────────────────────────────
log "=== 설정 완료 ==="
log "결과: 필수 OK · 선택 경고 $WARN_COUNT 개"
log ""
log "다음 단계:"
log "  1. (선택) templates/ 폴더에 회사 .pptx 추가"
log "  2. 이 디렉토리에서 'claude' 실행 후 '/rfp <RFP 파일>'"
log "     또는 직접 빌드: python3 scripts/yaml_to_pptx.py <콘텐츠.yaml> <out.pptx> --template <name>"
log ""
log "전체 로그: $LOGFILE"
exit 0
