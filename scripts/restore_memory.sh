#!/bin/bash
# 인수인계 메모리 복원 — docs/handover-memory/ → ~/.claude/projects/.../memory/
# 다른 PC 에서 clone 후 1회 실행.

set -e
SRC="$(dirname "$0")/../docs/handover-memory"
DEST="$HOME/.claude/projects/D--work-dabeeo-dsi/memory"

mkdir -p "$DEST"
cp -v "$SRC"/*.md "$DEST"/
echo ""
echo "복원 완료: $DEST"
ls -la "$DEST"
