#!/bin/bash
# hermes-audit.sh — 자가검증 크론 (30분마다)
# 패턴 성숙도, 규칙 무결성, 태스크 상태 감사
set -euo pipefail

BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
LOG="$BRAIN_DIR/scripts/audit.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

notify() {
  if [ -f "$BRAIN_DIR/scripts/notify.sh" ]; then
    "$BRAIN_DIR/scripts/notify.sh" "$1" "system" "${2:-info}" 2>/dev/null || true
  fi
}

echo "[$TIMESTAMP] [AUDIT] start" >> "$LOG"

# 1. 패턴 성숙도
TOTAL=$(ls "$BRAIN_DIR/vault/patterns/"*.md 2>/dev/null | wc -l | tr -d ' ')
PROMOTED=$(grep -rl "status: promoted" "$BRAIN_DIR/vault/patterns/" 2>/dev/null | wc -l | tr -d ' ')
CANDIDATES=$(grep -rl "status: candidate" "$BRAIN_DIR/vault/patterns/" 2>/dev/null | wc -l | tr -d ' ')
echo "[$TIMESTAMP] patterns: total=$TOTAL promoted=$PROMOTED candidates=$CANDIDATES" >> "$LOG"

# 2. CLAUDE.md 존재 확인
if [ ! -f "$BRAIN_DIR/CLAUDE.md" ]; then
  notify "CLAUDE.md missing!" "error"
fi

# 3. rules/ 파일 확인
RULES=$(ls "$BRAIN_DIR/rules/"*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$RULES" -lt 1 ]; then
  notify "rules/ is empty!" "error"
fi

# 4. 태스크큐 리뷰 대기
REVIEW_TASKS=""
for qf in "$BRAIN_DIR"/task-queue-*.json; do
  [ -f "$qf" ] || continue
  REVIEWS=$(python3 -c "
import json
d = json.load(open('$qf'))
for t in d.get('tasks', []):
    if t.get('status') == 'review':
        print(f\"{t['id']}: {t.get('task', '')[:60]}\")
" 2>/dev/null)
  if [ -n "$REVIEWS" ]; then
    REVIEW_TASKS="${REVIEW_TASKS}${REVIEWS}\n"
  fi
done

if [ -n "$REVIEW_TASKS" ]; then
  COUNT=$(echo -e "$REVIEW_TASKS" | grep -c . || true)
  notify "Review waiting: ${COUNT} tasks" "review"
fi

# 5. 로그 트림
if [ -f "$LOG" ] && [ $(wc -l < "$LOG") -gt 500 ]; then
  tail -200 "$LOG" > "${LOG}.tmp"
  mv "${LOG}.tmp" "$LOG"
fi

echo "[$TIMESTAMP] [AUDIT] done" >> "$LOG"
