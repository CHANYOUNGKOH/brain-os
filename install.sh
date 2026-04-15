#!/bin/bash
# Brain OS — Install Script
# 로컬 PC에서 자가학습 AI 에이전트 시스템 셋업
set -euo pipefail

BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

echo "🧠 Brain OS Installer"
echo "====================="
echo "Install directory: $BRAIN_DIR"
echo ""

# ── 1. 디렉토리 구조 ────────────────────────
echo "[1/7] Creating directory structure..."
mkdir -p "$BRAIN_DIR"/{rules,vault/{raw,entities,concepts,comparisons,queries,patterns},skills,memory,scripts}

# ── 2. 스크립트 복사 ────────────────────────
echo "[2/7] Copying scripts..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)/scripts"
if [ -d "$SCRIPT_DIR" ]; then
  cp "$SCRIPT_DIR"/*.py "$BRAIN_DIR/scripts/" 2>/dev/null || true
  cp "$SCRIPT_DIR"/*.sh "$BRAIN_DIR/scripts/" 2>/dev/null || true
  chmod +x "$BRAIN_DIR/scripts/"*.sh 2>/dev/null || true
  chmod +x "$BRAIN_DIR/scripts/"*.py 2>/dev/null || true
fi

# ── 3. CLAUDE.md 생성 ────────────────────────
echo "[3/7] Creating CLAUDE.md..."
if [ ! -f "$BRAIN_DIR/CLAUDE.md" ]; then
  TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)/templates"
  if [ -f "$TEMPLATE_DIR/CLAUDE.md" ]; then
    cp "$TEMPLATE_DIR/CLAUDE.md" "$BRAIN_DIR/CLAUDE.md"
  else
    cat > "$BRAIN_DIR/CLAUDE.md" << 'CLAUDE_EOF'
# Brain OS — Self-Improving Agent

## 자동 학습 (항상 활성 — 강제)
대화 중 다음을 자동 수행:
1. **패턴 감지** — 반복 요청, 에러 해결, 사용자 교정, 워크플로우 발견 시
2. **한 줄 알림 후 기록** — `vault/patterns/`에 저장 (묵묵히 기록 금지)
3. **검증된 패턴은 승격** — 사용자 확인 후 `rules/`에 영구 등록

### 강제 규칙 (스킵 = 위반)
- 사용자 교정 감지 시 → **현재 작업보다 기록이 우선**
- 부정어/의문형 교정(안돼, 하지마, 왜, 거기 아님) → 즉시 패턴 기록
- system-reminder 자가학습 리마인더 = 참고가 아니라 **행동 명령**
- 매 응답 전 셀프 체크: "교정/발견 있었는데 기록 안 한 거 있나?"

## SI 명령어
- `si:review` — 패턴 분석, 승격 후보, stale 정리
- `si:promote [패턴]` — 규칙으로 영구 승격
- `si:extract [패턴]` — 범용 스킬로 추출
- `si:status` — 학습 현황 대시보드
- `si:remember [내용]` — 즉시 기억 저장

## Vault
- 지식 저장소: `vault/`
- 구조: raw/ entities/ concepts/ comparisons/ queries/ **patterns/**

## 톤
간결, 직접적.
CLAUDE_EOF
  fi
  echo "  Created: $BRAIN_DIR/CLAUDE.md"
else
  echo "  Skipped: CLAUDE.md already exists"
fi

# ── 4. 규칙 파일 생성 ────────────────────────
echo "[4/7] Creating initial rules..."
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)/templates"

if [ ! -f "$BRAIN_DIR/rules/core.md" ]; then
  cat > "$BRAIN_DIR/rules/core.md" << 'EOF'
# Core Rules

1. **소통 우선** — 작업 전 의도 확인, 진행 중 상태 보고, 완료 후 요약
2. **학습 축적** — 사용자 피드백, 패턴, 교정을 vault에 기록
3. **자율 실행 금지** — 각 단계 소통 필수
EOF
fi

if [ ! -f "$BRAIN_DIR/rules/self-improving.md" ]; then
  if [ -f "$TEMPLATE_DIR/self-improving.md" ]; then
    cp "$TEMPLATE_DIR/self-improving.md" "$BRAIN_DIR/rules/self-improving.md"
  else
    cat > "$BRAIN_DIR/rules/self-improving.md" << 'EOF'
# Self-Improving — 자동 학습 루프

## 패턴 감지 트리거
- **반복 요청**: 동일/유사 요청 2회 이상
- **에러 해결**: 새 해결법 발견
- **사용자 교정**: 행동/판단 수정
- **워크플로우 발견**: 작업 순서 반복
- **선호 표현**: 명시적/암시적 선호

## 강제 감지 규칙
1. 부정어/의문형 교정 → 즉시 패턴 기록
2. 매 응답 전 셀프 체크: "기록 안 한 교정/발견 있나?"
3. system-reminder = 행동 명령
EOF
  fi
fi

# ── 5. Holographic memory 셋업 ────────────────────────
echo "[5/7] Setting up Holographic memory..."
HOLO_DIR="$BRAIN_DIR/holographic"
if [ ! -d "$HOLO_DIR" ]; then
  mkdir -p "$HOLO_DIR"
  # 기본 holographic 모듈 복사
  HOLO_SRC="$(cd "$(dirname "$0")" && pwd)/scripts/holographic"
  if [ -d "$HOLO_SRC" ]; then
    cp -r "$HOLO_SRC"/* "$HOLO_DIR/"
  else
    # 최소 SQLite 기반 메모리 스토어 생성
    cat > "$HOLO_DIR/store.py" << 'PYEOF'
"""Minimal fact store — SQLite based."""
import sqlite3
from pathlib import Path

class MemoryStore:
    def __init__(self, db_path):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT 'general',
                trust_score REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def add_fact(self, content, category='general'):
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO facts (content, category) VALUES (?, ?)",
                (content, category)
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            pass

    def search_facts(self, query, limit=10):
        cursor = self._conn.execute(
            "SELECT * FROM facts WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor]

    def list_facts(self, limit=50):
        cursor = self._conn.execute("SELECT * FROM facts ORDER BY created_at DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor]

    def close(self):
        self._conn.close()
PYEOF
  fi
  echo "  Created: $HOLO_DIR"
else
  echo "  Skipped: holographic already exists"
fi

# ── 6. Claude Code hooks 설정 ────────────────────────
echo "[6/7] Configuring Claude Code hooks..."
mkdir -p "$HOME/.claude"

if [ -f "$CLAUDE_SETTINGS" ]; then
  echo "  Warning: $CLAUDE_SETTINGS already exists"
  echo "  To add hooks manually, see templates/settings.json"
else
  cat > "$CLAUDE_SETTINGS" << HOOKEOF
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$BRAIN_DIR/scripts/si-pattern-check.sh 2>/dev/null || true",
            "timeout": 10,
            "statusMessage": "SI pattern check..."
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"UserPromptSubmit\",\"additionalContext\":\"Self-improving: Record patterns for user corrections, repeated requests, error resolutions, workflow discoveries in vault/patterns/. Always notify before recording.\"}}'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
HOOKEOF
  echo "  Created: $CLAUDE_SETTINGS"
fi

# ── 7. Cron 등록 ────────────────────────
echo "[7/7] Setting up cron jobs..."
CRON_MARKER="# Brain OS"

if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
  echo "  Skipped: Brain OS cron jobs already registered"
else
  # 기존 crontab 보존 + 추가
  (
    crontab -l 2>/dev/null || true
    echo ""
    echo "$CRON_MARKER"
    echo "# Capture Pipeline — browser history (daily 23:00 local)"
    echo "0 23 * * * /usr/bin/python3 $BRAIN_DIR/scripts/capture-history.py >> $BRAIN_DIR/scripts/capture.log 2>&1"
    echo "# User Model Update (daily 23:30)"
    echo "30 23 * * * /usr/bin/python3 $BRAIN_DIR/scripts/user-model-update.py >> $BRAIN_DIR/scripts/user-model.log 2>&1"
    echo "# Auto-Memorize (daily 23:45)"
    echo "45 23 * * * /usr/bin/python3 $BRAIN_DIR/scripts/auto-memorize.py >> $BRAIN_DIR/scripts/memorize.log 2>&1"
    echo "# Vault Hygiene (daily 04:00)"
    echo "0 4 * * * $BRAIN_DIR/scripts/vault-hygiene.sh >> $BRAIN_DIR/scripts/vault-hygiene.log 2>&1"
    echo "# Self-Audit (every 30min)"
    echo "*/30 * * * * $BRAIN_DIR/scripts/si-pattern-check.sh >> $BRAIN_DIR/scripts/audit.log 2>&1"
  ) | crontab -
  echo "  Registered 5 cron jobs"
fi

echo ""
echo "✅ Brain OS installed successfully!"
echo ""
echo "Next steps:"
echo "  1. cd $BRAIN_DIR"
echo "  2. Open Claude Code — CLAUDE.md will auto-load"
echo "  3. Start talking — the system learns automatically"
echo ""
echo "Commands:"
echo "  si:status  — learning dashboard"
echo "  si:review  — review patterns"
echo "  si:promote — promote pattern to rule"
