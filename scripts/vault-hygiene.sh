#!/bin/bash
# vault-hygiene.sh — 일 1회 vault 정리
set -euo pipefail

BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
LOG="$BRAIN_DIR/scripts/vault-hygiene.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] vault-hygiene 시작" >> "$LOG"

# 1. stale 패턴 (30일 이상 candidate)
STALE=$(python3 -c "
import os, re
from datetime import datetime, timedelta
cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
pat_dir = '$BRAIN_DIR/vault/patterns'
if not os.path.isdir(pat_dir):
    exit()
for f in os.listdir(pat_dir):
    if not f.endswith('.md'): continue
    text = open(os.path.join(pat_dir, f)).read()
    if 'status: candidate' not in text: continue
    m = re.search(r'created:\s*(\S+)', text)
    if m and m.group(1) < cutoff:
        print(f)
" 2>/dev/null)

if [ -n "$STALE" ]; then
  COUNT=$(echo "$STALE" | wc -l | tr -d ' ')
  echo "[$TIMESTAMP] stale 패턴 ${COUNT}개 발견" >> "$LOG"
  for f in $STALE; do
    python3 -c "
path = '$BRAIN_DIR/vault/patterns/$f'
text = open(path).read()
text = text.replace('status: candidate', 'status: stale-archived')
open(path, 'w').write(text)
" 2>/dev/null
  done
fi

# 2. rules/ 무결성
RULES_COUNT=$(ls "$BRAIN_DIR/rules/"*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$RULES_COUNT" -lt 1 ]; then
  echo "[$TIMESTAMP] 경고: rules/ 비어있음" >> "$LOG"
fi

# 3. skill 승격 후보 체크
if [ -f "$BRAIN_DIR/scripts/skill-promoter.py" ]; then
  python3 "$BRAIN_DIR/scripts/skill-promoter.py" >> "$LOG" 2>/dev/null || true
fi

# 4. 로그 트림
if [ -f "$LOG" ] && [ $(wc -l < "$LOG") -gt 500 ]; then
  tail -200 "$LOG" > "${LOG}.tmp"
  mv "${LOG}.tmp" "$LOG"
fi

echo "[$TIMESTAMP] vault-hygiene 완료" >> "$LOG"
