#!/bin/bash
# Close Captured Tabs — 캡처 완료된 Chrome 탭 자동 닫기
# AppleScript로 Chrome 탭 매칭 → 닫기
#
# 사용법:
#   close-captured-tabs.sh                    # 어제 캡처된 URL 기준
#   close-captured-tabs.sh 2026-04-14         # 특정 날짜
#   close-captured-tabs.sh --dry-run          # 닫지 않고 목록만 출력

set -euo pipefail

VAULT="$HOME/.hermes/vault"
DATE="${1:-$(date -v-1d +%Y-%m-%d)}"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]] || [[ "${2:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

# 캡처된 URL 목록 수집
CAPTURED_URLS=()

# history 파일에서 URL 추출
HISTORY_FILE="$VAULT/raw/history-${DATE}.md"
if [[ -f "$HISTORY_FILE" ]]; then
  while IFS= read -r url; do
    CAPTURED_URLS+=("$url")
  done < <(grep -oP 'https?://[^\)]+' "$HISTORY_FILE" 2>/dev/null | head -50)
fi

# playwright capture 파일에서 URL 추출
for f in "$VAULT/raw/capture-${DATE}-"*.md; do
  if [[ -f "$f" ]]; then
    url=$(grep "^url:" "$f" 2>/dev/null | head -1 | sed 's/url: //')
    if [[ -n "$url" ]]; then
      CAPTURED_URLS+=("$url")
    fi
  fi
done

if [[ ${#CAPTURED_URLS[@]} -eq 0 ]]; then
  echo "[close-tabs] no captured URLs for $DATE"
  exit 0
fi

echo "[close-tabs] found ${#CAPTURED_URLS[@]} captured URLs for $DATE"

# Chrome 탭 닫기 (AppleScript)
CLOSED=0
for url in "${CAPTURED_URLS[@]}"; do
  # URL에서 도메인+경로 추출 (쿼리 파라미터 제거)
  match_url="${url%%\?*}"

  if $DRY_RUN; then
    echo "  [dry-run] would close: $match_url"
    continue
  fi

  # AppleScript로 Chrome 탭 매칭 + 닫기
  result=$(osascript -e "
    tell application \"Google Chrome\"
      set closedCount to 0
      repeat with w in windows
        set tabList to tabs of w
        repeat with i from (count of tabList) to 1 by -1
          set t to item i of tabList
          if URL of t contains \"${match_url}\" then
            close t
            set closedCount to closedCount + 1
          end if
        end repeat
      end repeat
      return closedCount
    end tell
  " 2>/dev/null || echo "0")

  if [[ "$result" -gt 0 ]]; then
    echo "  closed $result tab(s): ${match_url:0:80}"
    CLOSED=$((CLOSED + result))
  fi
done

echo "[close-tabs] done: $CLOSED tabs closed"

# 로그
LOG="$VAULT/log.md"
if [[ -f "$LOG" ]] && ! $DRY_RUN && [[ $CLOSED -gt 0 ]]; then
  echo "- [$(date +%Y-%m-%d)] close-captured-tabs: $CLOSED tabs closed" >> "$LOG"
fi
