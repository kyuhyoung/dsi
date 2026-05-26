#!/bin/bash
# 인수인계 메모리 복원 — docs/handover-memory/ → ~/.claude/projects/<slug>/memory/
# WSL Linux / macOS 호환. clone 후 1회 실행.
#
# slug 자동 생성 — 프로젝트 절대 경로의 슬래시/콜론을 '-' 로 변환
#   /mnt/d/work/dabeeo/dsi → -mnt-d-work-dabeeo-dsi  (WSL)
#   /Users/kevin/dsi       → -Users-kevin-dsi        (macOS)

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SRC="$PROJECT_ROOT/docs/handover-memory"
# 경로 → Claude Code slug (슬래시/콜론/역슬래시를 '-' 로)
SLUG="$(echo "$PROJECT_ROOT" | sed 's/[\/:\\]/-/g')"
DEST="$HOME/.claude/projects/$SLUG/memory"

echo "프로젝트 경로: $PROJECT_ROOT"
echo "slug: $SLUG"
echo "복원 대상: $DEST"
echo ""

mkdir -p "$DEST"
cp -v "$SRC"/*.md "$DEST"/
echo ""
echo "복원 완료: $DEST"
ls -la "$DEST"
