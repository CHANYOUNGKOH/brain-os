#!/bin/bash
# Brain OS — Install Script
# 로컬 PC에서 자가학습 AI 에이전트 시스템 셋업
# 자가학습 + 에이전트 위임 + 텔레그램/디스코드 알림
set -euo pipefail

BRAIN_DIR="${BRAIN_OS_DIR:-$HOME/.brain-os}"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🧠 Brain OS Installer"
echo "====================="
echo "Install directory: $BRAIN_DIR"
echo ""

# ── 1. 디렉토리 구조 ────────────────────────
echo "[1/9] Creating directory structure..."
mkdir -p "$BRAIN_DIR"/{rules,vault/{raw,entities,concepts,comparisons,queries,patterns},skills,memory,scripts/agents}

# ── 2. 스크립트 복사 ────────────────────────
echo "[2/9] Copying scripts..."
cp "$SRC_DIR/scripts/"*.py "$BRAIN_DIR/scripts/" 2>/dev/null || true
cp "$SRC_DIR/scripts/"*.sh "$BRAIN_DIR/scripts/" 2>/dev/null || true
cp "$SRC_DIR/scripts/agents/"*.py "$BRAIN_DIR/scripts/agents/" 2>/dev/null || true
cp "$SRC_DIR/scripts/agents/"*.sh "$BRAIN_DIR/scripts/agents/" 2>/dev/null || true
chmod +x "$BRAIN_DIR/scripts/"*.sh "$BRAIN_DIR/scripts/"*.py 2>/dev/null || true
chmod +x "$BRAIN_DIR/scripts/agents/"*.sh "$BRAIN_DIR/scripts/agents/"*.py 2>/dev/null || true

# ── 3. CLAUDE.md 생성 ────────────────────────
echo "[3/9] Creating CLAUDE.md..."
if [ ! -f "$BRAIN_DIR/CLAUDE.md" ]; then
  cp "$SRC_DIR/templates/CLAUDE.md" "$BRAIN_DIR/CLAUDE.md"
  echo "  Created: $BRAIN_DIR/CLAUDE.md"
else
  echo "  Skipped: CLAUDE.md already exists"
fi

# ── 4. 규칙 파일 생성 ────────────────────────
echo "[4/9] Creating initial rules..."
if [ ! -f "$BRAIN_DIR/rules/core.md" ]; then
  cat > "$BRAIN_DIR/rules/core.md" << 'EOF'
# Core Rules

1. **소통 우선** — 작업 전 의도 확인, 진행 중 상태 보고, 완료 후 요약
2. **위임 전문** — 도메인 에이전트에 위임, 직접 코드 수정 금지
3. **학습 축적** — 사용자 피드백, 패턴, 교정을 vault에 기록
4. **단일책임 경계** — 역할 경계 = 에이전트 경계
5. **자율 실행 금지** — 각 단계 소통 필수
EOF
fi

if [ ! -f "$BRAIN_DIR/rules/self-improving.md" ]; then
  cp "$SRC_DIR/templates/self-improving.md" "$BRAIN_DIR/rules/self-improving.md"
fi

# ── 5. Holographic memory 셋업 ────────────────────────
echo "[5/9] Setting up Holographic memory..."
HOLO_DIR="$BRAIN_DIR/holographic"
if [ ! -d "$HOLO_DIR" ]; then
  mkdir -p "$HOLO_DIR"
  if [ -d "$SRC_DIR/scripts/holographic" ]; then
    cp -r "$SRC_DIR/scripts/holographic/"* "$HOLO_DIR/"
  else
    cat > "$HOLO_DIR/store.py" << 'PYEOF'
"""Minimal fact store — SQLite based."""
import sqlite3

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
        cursor = self._conn.execute(
            "SELECT * FROM facts ORDER BY created_at DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor]

    def close(self):
        self._conn.close()
PYEOF
  fi
  echo "  Created: $HOLO_DIR"
fi

# ── 6. 환경변수 파일 ────────────────────────
echo "[6/9] Setting up configuration..."
if [ ! -f "$BRAIN_DIR/brain-os.env" ]; then
  cp "$SRC_DIR/brain-os.env.example" "$BRAIN_DIR/brain-os.env"
  echo "  Created: $BRAIN_DIR/brain-os.env (edit with your tokens)"
else
  echo "  Skipped: brain-os.env already exists"
fi

# ── 7. 태스크큐 초기화 ────────────────────────
echo "[7/9] Setting up task queues..."
# brain-os.env에서 도메인 읽기
if [ -f "$BRAIN_DIR/brain-os.env" ]; then
  DOMAINS=$(grep "^BRAIN_OS_DOMAINS" "$BRAIN_DIR/brain-os.env" 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "")
fi
DOMAINS="${DOMAINS:-trading content infra}"

for domain in $DOMAINS; do
  QUEUE="$BRAIN_DIR/task-queue-${domain}.json"
  if [ ! -f "$QUEUE" ]; then
    echo "{\"version\": 1, \"project\": \"$domain\", \"tasks\": []}" > "$QUEUE"
    echo "  Created: $QUEUE"
  fi
done

# ── 8. Claude Code hooks 설정 ────────────────────────
echo "[8/9] Configuring Claude Code hooks..."
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

# ── 9. Cron 등록 ────────────────────────
echo "[9/9] Setting up cron jobs..."
CRON_MARKER="# Brain OS"

if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
  echo "  Skipped: Brain OS cron jobs already registered"
else
  (
    crontab -l 2>/dev/null || true
    echo ""
    echo "$CRON_MARKER"
    echo "# Self-Audit (every 30min)"
    echo "*/30 * * * * $BRAIN_DIR/scripts/hermes-audit.sh >> $BRAIN_DIR/scripts/audit.log 2>&1"
    echo "# Agent Loops — per domain (20:00-07:59 window)"
    for domain in $DOMAINS; do
      echo "*/30 11-14,15-22 * * * $BRAIN_DIR/scripts/agents/agent-loop.sh $domain >> $BRAIN_DIR/scripts/agent-loop.log 2>&1"
    done
    echo "# Capture Pipeline — browser history (daily 23:00)"
    echo "0 23 * * * /usr/bin/python3 $BRAIN_DIR/scripts/capture-history.py >> $BRAIN_DIR/scripts/capture.log 2>&1"
    echo "# User Model Update (daily 23:30)"
    echo "30 23 * * * /usr/bin/python3 $BRAIN_DIR/scripts/user-model-update.py >> $BRAIN_DIR/scripts/user-model.log 2>&1"
    echo "# Auto-Memorize (daily 23:45)"
    echo "45 23 * * * /usr/bin/python3 $BRAIN_DIR/scripts/auto-memorize.py >> $BRAIN_DIR/scripts/memorize.log 2>&1"
    echo "# Vault Hygiene (daily 04:00)"
    echo "0 4 * * * $BRAIN_DIR/scripts/vault-hygiene.sh >> $BRAIN_DIR/scripts/vault-hygiene.log 2>&1"
  ) | crontab -
  CRON_COUNT=$(( 3 + $(echo "$DOMAINS" | wc -w | tr -d ' ') + 4 ))
  echo "  Registered cron jobs"
fi

echo ""
echo "============================================"
echo "✅ Brain OS installed successfully!"
echo "============================================"
echo ""
echo "Directory: $BRAIN_DIR"
echo "Domains:   $DOMAINS"
echo ""
echo "Next steps:"
echo "  1. Edit $BRAIN_DIR/brain-os.env with your Telegram/Discord tokens"
echo "  2. cd $BRAIN_DIR && open Claude Code"
echo "  3. CLAUDE.md auto-loads → self-improving agent active"
echo ""
echo "Task delegation:"
echo "  dispatch-now.sh {domain} [task-id]  — trigger agent now"
echo "  task-approve.py {queue} {task-id}   — approve reviewed task"
echo ""
echo "Learning commands (in Claude Code):"
echo "  si:status   — learning dashboard"
echo "  si:review   — review patterns for promotion"
echo "  si:promote  — promote pattern to permanent rule"
echo "  si:remember — save a fact immediately"
