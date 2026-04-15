#!/bin/bash
# agent-loop.sh — 범용 에이전트 루프
# crontab: */30 20-23,0-7 * * * agent-loop.sh {domain}
# 또는 dispatch-now.sh에서 호출
set -euo pipefail

BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
DOMAIN="${1:?Usage: agent-loop.sh {domain}}"
CLAUDE="${CLAUDE_CMD:-$HOME/.local/bin/claude}"
QUEUE="$BRAIN_DIR/task-queue-${DOMAIN}.json"
LOG="$BRAIN_DIR/scripts/agent-loop.log"
LOCK="/tmp/brain-os-loop-${DOMAIN}.lock"

# 알림 함수 (telegram, discord 등 — 설정 없으면 stdout)
notify() {
  local msg="$1"
  local level="${2:-info}"
  echo "$(date '+%Y-%m-%d %H:%M:%S') [$DOMAIN/$level] $msg" >> "$LOG"
  if [ -f "$BRAIN_DIR/scripts/notify.sh" ]; then
    "$BRAIN_DIR/scripts/notify.sh" "$msg" "$DOMAIN" "$level" 2>/dev/null || true
  fi
}

# macOS 호환 timeout
run_with_timeout() {
  local secs=$1; shift
  "$@" &
  local pid=$!
  ( sleep "$secs" && kill "$pid" 2>/dev/null ) &
  local watcher=$!
  wait "$pid" 2>/dev/null
  local ret=$?
  kill "$watcher" 2>/dev/null
  wait "$watcher" 2>/dev/null
  return $ret
}

# 중복 실행 방지
if [ -f "$LOCK" ]; then
  PID=$(cat "$LOCK")
  if kill -0 "$PID" 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$DOMAIN/SKIP] already running (PID $PID)" >> "$LOG"
    exit 0
  fi
fi
echo $$ > "$LOCK"
trap "rm -f $LOCK" EXIT

# 큐 파일 확인
if [ ! -f "$QUEUE" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [$DOMAIN/SKIP] no queue file" >> "$LOG"
  exit 0
fi

# 다음 태스크 찾기
RESULT=$(python3 "$BRAIN_DIR/scripts/agents/dispatch-check.py" "$QUEUE" 2>/dev/null)

if [[ "$RESULT" == DISPATCH:* ]]; then
  INFO="${RESULT#DISPATCH:}"
  TASK_ID=$(echo "$INFO" | cut -d'|' -f1)
  AGENT=$(echo "$INFO" | cut -d'|' -f2)
  TASK=$(echo "$INFO" | cut -d'|' -f3)
  DC=$(echo "$INFO" | cut -d'|' -f4)

  notify "$TASK_ID → $AGENT: $TASK (attempt $((DC+1))/3)" "dispatch"

  # dispatch_count 증가
  python3 -c "
import json
with open('$QUEUE') as f:
    d = json.load(f)
for t in d['tasks']:
    if t['id'] == '$TASK_ID':
        t['dispatch_count'] = t.get('dispatch_count', 0) + 1
        break
with open('$QUEUE', 'w') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
" 2>/dev/null

  START_SEC=$(date +%s)

  # Claude CLI 실행
  if $CLAUDE --version >/dev/null 2>&1; then
    TASK_OUTPUT=$(run_with_timeout 300 $CLAUDE -p \
      --output-format text --permission-mode bypassPermissions \
      "Task $TASK_ID: $TASK

Rules:
- If you know the target file, modify it directly. Minimize exploration.
- Write/Edit immediately. Don't just plan.
- Report: changed files + one-line summary.
- Do NOT modify the task-queue JSON." \
      2>> "$LOG") || true
    RET=$?
  else
    notify "Claude CLI not available — dispatch failed ($TASK_ID)" "error"
    RET=1
    TASK_OUTPUT=""
  fi

  ELAPSED=$(( $(date +%s) - START_SEC ))
  notify "$TASK_ID done (${ELAPSED}s, exit=$RET)" "complete"

  # review 상태로 변경
  PREVIEW=$(echo "$TASK_OUTPUT" | tail -3 | head -200)
  python3 "$BRAIN_DIR/scripts/agents/task-set-review.py" "$QUEUE" "$TASK_ID" "$PREVIEW" "$RET" "$ELAPSED" 2>/dev/null

  if [ $RET -ne 0 ]; then
    notify "REVIEW NEEDED (failed): $TASK_ID — $TASK (exit=$RET)" "error"
  else
    notify "REVIEW NEEDED: $TASK_ID — $TASK (${ELAPSED}s)" "review"
  fi

elif [[ "$RESULT" == BLOCKED:* ]]; then
  notify "Tasks blocked: $RESULT" "warn"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') [$DOMAIN/IDLE] no pending tasks" >> "$LOG"
fi
