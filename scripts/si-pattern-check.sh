#!/bin/bash
# SI Pattern Check — candidate 패턴 수 체크, 5개 이상이면 리뷰 권고
BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
PATTERNS_DIR="$BRAIN_DIR/vault/patterns"

if [ ! -d "$PATTERNS_DIR" ]; then
  exit 0
fi

COUNT=$(grep -rl "status: candidate" "$PATTERNS_DIR" 2>/dev/null | wc -l | tr -d ' ')

if [ "$COUNT" -ge 5 ]; then
  echo "⚡ $COUNT candidate patterns pending — consider running si:review"
fi
