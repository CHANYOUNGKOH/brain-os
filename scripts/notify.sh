#!/bin/bash
# notify.sh — 알림 라우터 (telegram, discord, stdout)
# Usage: notify.sh "message" "domain" "level"
# 설정: brain-os.env에서 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 등

BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
ENV_FILE="$BRAIN_DIR/brain-os.env"

MSG="$1"
DOMAIN="${2:-general}"
LEVEL="${3:-info}"

# 환경변수 로드
if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE"
fi

# 텔레그램
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  python3 "$BRAIN_DIR/scripts/send-telegram.py" "$MSG" "$DOMAIN" 2>/dev/null || true
fi

# 디스코드
if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
  curl -s -H "Content-Type: application/json" \
    -d "{\"content\": \"[$DOMAIN/$LEVEL] $MSG\"}" \
    "$DISCORD_WEBHOOK_URL" 2>/dev/null || true
fi

# 항상 stdout
echo "[$DOMAIN/$LEVEL] $MSG"
