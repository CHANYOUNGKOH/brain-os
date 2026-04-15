#!/bin/bash
# dispatch-now.sh — 즉시 위임 트리거
# 사용: dispatch-now.sh {domain} [task-id]
# task-id 없으면 큐의 첫 번째 pending 태스크를 실행
set -euo pipefail

BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
DOMAIN="$1"
TASK_ID="${2:-}"
LOG="$BRAIN_DIR/scripts/dispatch.log"

if [ -z "$DOMAIN" ]; then
  echo "Usage: dispatch-now.sh {domain-name} [task-id]"
  echo "Domains are configured in brain-os.conf"
  exit 1
fi

SCRIPT="$BRAIN_DIR/scripts/agents/agent-loop.sh"
QUEUE="$BRAIN_DIR/task-queue-${DOMAIN}.json"

if [ ! -f "$QUEUE" ]; then
  echo "Error: queue not found: $QUEUE"
  exit 1
fi

# 특정 task-id 확인
if [ -n "$TASK_ID" ]; then
  python3 -c "
import json
with open('$QUEUE') as f:
    d = json.load(f)
found = False
for t in d['tasks']:
    if t['id'] == '$TASK_ID':
        if t['status'] != 'pending':
            print(f'Warning: {t[\"id\"]} is {t[\"status\"]} (not pending)')
        found = True
        break
if not found:
    print(f'Error: $TASK_ID not found')
else:
    print(f'Target: $TASK_ID')
" 2>/dev/null
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') [DISPATCH] $DOMAIN (task: ${TASK_ID:-auto})" >> "$LOG"

# 락 파일 체크
LOCK="/tmp/brain-os-loop-${DOMAIN}.lock"
if [ -f "$LOCK" ]; then
  OLD_PID=$(cat "$LOCK")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Already running (PID $OLD_PID)"
    exit 1
  fi
  rm -f "$LOCK"
fi

# 실행
exec "$SCRIPT" "$DOMAIN"
