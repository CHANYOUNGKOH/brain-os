# Brain OS — Self-Improving AI Agent System

> "저장이 아니라 학습, 검색이 아니라 재사용, 기록이 아니라 사용자를 더 깊이 이해하는 운영 체계"

Claude Code Max 단일 구독으로 운영하는 자가학습 AI PM 에이전트 시스템.  
외부 유료 API 0원. 로컬 PC만으로 완전 동작.

## What is this?

Brain OS는 AI 에이전트가 단순 명령 실행을 넘어 **사용자를 학습하고, 패턴을 감지하고, 스스로 규칙을 만들어가는** 시스템이다.

### Core Loop
```
사용자 교정/피드백 → 패턴 감지 → vault 기록 → 검증 → 규칙 승격 → 행동 반영
```

### Architecture
```
Claude Code Max (엔진)
├── CLAUDE.md (시스템 프롬프트 + 강제 규칙)
├── rules/ (영구 규칙 — 승격된 패턴)
├── vault/ (지식 저장소)
│   └── patterns/ (감지된 패턴)
├── scripts/
│   ├── capture-history.py     — 브라우저 히스토리 수집
│   ├── user-model-update.py   — 사용자 이해 엔진
│   ├── auto-memorize.py       — 대화→사실 자동 추출
│   ├── skill-promoter.py      — 성공 패턴→skill 승격
│   ├── vault-hygiene.sh       — stale 정리 + 무결성
│   ├── hermes-audit.sh        — 30분 자가 감사
│   ├── notify.sh              — 알림 라우터 (Telegram/Discord)
│   ├── send-telegram.py       — 텔레그램 메시지/파일 전송
│   └── agents/
│       ├── agent-loop.sh      — 범용 에이전트 루프
│       ├── dispatch-now.sh    — 즉시 위임 트리거
│       ├── dispatch-check.py  — 다음 태스크 찾기
│       ├── task-set-review.py — 완료→리뷰 상태 전환
│       └── task-approve.py    — 리뷰→완료 승인
├── task-queue-{domain}.json (도메인별 태스크큐)
├── brain-os.env (Telegram/Discord 토큰)
├── skills/ (도메인 스킬)
└── memory/ (세션 기록)
```

## Quick Start

### Requirements
- **Claude Code Max** subscription ($100/mo or $200/mo) — only paid item
- **Python 3.9+**
- **Git**
- macOS, Linux, or Windows

### Install

**macOS / Linux:**
```bash
git clone https://github.com/Kokoko9494/brain-os.git ~/.brain-os
cd ~/.brain-os
./install.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/Kokoko9494/brain-os.git $env:USERPROFILE\.brain-os
cd $env:USERPROFILE\.brain-os
python install.sh  # or: ask Claude Code to set it up
```

**Or just ask Claude Code:**
```
cd ~/.brain-os   (or %USERPROFILE%\.brain-os on Windows)
# Open Claude Code, then say:
"Brain OS 셋업해줘" or "Set up Brain OS"
# Claude reads CLAUDE.md and handles the rest for your platform
```

### What gets set up
1. Directory structure (vault, rules, skills, memory, scripts)
2. CLAUDE.md (system prompt with self-improving rules)
3. Claude Code hooks (learning reminders)
4. Scheduled tasks (capture, analysis, cleanup)
5. Task queues for agent delegation
6. Notification setup (Telegram/Discord — optional)

### Platform-specific notes

| Feature | macOS | Linux | Windows |
|---------|-------|-------|---------|
| Scheduler | crontab | crontab | Task Scheduler (schtasks) |
| Chrome History | ✅ | ✅ | ✅ |
| Safari History | ✅ | — | — |
| Telegram/Discord | ✅ | ✅ | ✅ |
| Claude Code | ✅ | ✅ | ✅ |

Use `python scripts/scheduler.py install` for cross-platform schedule setup.

### Start using
```bash
cd ~/.brain-os
# Claude Code auto-loads CLAUDE.md
# Start talking — the system learns automatically
```

## Components

### 1. Self-Improving Loop (자가학습)

3계층 자동 학습:

| Layer | Trigger | Action |
|-------|---------|--------|
| **Hook** | 매 사용자 입력 | 교정/패턴 즉시 감지 + 기록 |
| **Cron** | 매일 23:00 | 히스토리 수집, 사용자 모델 갱신, 사실 축적 |
| **Audit** | 매 30분 | 규칙 무결성, stale 정리, 승격 후보 알림 |

### 2. Capture Pipeline (브라우저 히스토리)

```
Chrome/Safari History (로컬 SQLite)
→ 날짜별 필터 + 노이즈 제거
→ vault/raw/history-YYYY-MM-DD.md
→ High-value 페이지 별도 저장
```

- GitHub, Perplexity, Claude, StackOverflow 등 고가치 도메인 자동 마킹
- OAuth/login/auth URL 자동 필터링

### 3. User Understanding Engine (Honcho 대체)

```
대화 transcript (로컬 .jsonl)
→ 교정 패턴 분석 (부정어, 의문형)
→ 승인 패턴 분석 (ㅇㅇ, ㄱㄱ, 좋아)
→ 관심사 빈도 추적
→ 소통 스타일 정량화
→ user-model.json (구조화된 사용자 모델)
```

### 4. Holographic Memory (Supermemory 대체)

```
대화 transcript
→ 결정/규칙/발견/해결 사실 추출
→ SQLite + HRR 벡터 저장
→ 시맨틱 검색 가능
```

### 5. Skill Promotion (성공 절차 승격)

```
vault/patterns/ 스캔
→ hits >= 3 → 승격 후보
→ 완료 태스크 반복 패턴 감지
→ 알림 → 사용자 확인 → rules/ 영구 등록
```

## Tool Substitution Map

모든 유료 도구를 무료 로컬 대안으로 대체:

| Paid Tool | Free Alternative | How |
|-----------|-----------------|-----|
| Brave Search API | WebSearch | Claude 내장 |
| Parallel Search | WebSearch 다중 호출 | Claude 내장 |
| Firecrawl | WebFetch | Claude 내장 |
| Comet CDP | Playwright | 로컬 설치 |
| Honcho | user-model-update.py | 로컬 transcript 분석 |
| Supermemory | Holographic (SQLite+HRR) | 로컬 DB |
| Obsidian Vault | vault/ 디렉토리 | 파일 기반 |

## Configuration

### CLAUDE.md
시스템 프롬프트. 에이전트의 행동 규칙을 정의. `templates/CLAUDE.md` 참고.

### rules/
영구 규칙 파일. 검증된 패턴이 승격되는 곳.
- `core.md` — 핵심 원칙
- `self-improving.md` — 학습 루프 규칙
- 사용자 정의 규칙 추가 가능

### Hooks (settings.json)
```json
{
  "hooks": {
    "Stop": [{"hooks": [{"type": "command", "command": "si-pattern-check.sh"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "echo '자가학습 리마인더'"}]}]
  }
}
```

### Cron
```
*/30 * * * *  hermes-audit.sh          # 자가 감사
0    14 * * * capture-history.py        # 히스토리 수집 (23:00 KST)
30   14 * * * user-model-update.py      # 사용자 모델 갱신
45   14 * * * auto-memorize.py          # 사실 자동 축적
0    19 * * * vault-hygiene.sh          # vault 정리
0    0  * * 1 system-maturity.sh        # 주간 보고
```

## SI Commands

대화 중 사용할 수 있는 자가학습 명령어:

| Command | Action |
|---------|--------|
| `si:review` | 패턴 분석, 승격 후보 표시 |
| `si:promote [name]` | 규칙으로 영구 승격 |
| `si:extract [name]` | 범용 스킬로 추출 |
| `si:status` | 학습 현황 대시보드 |
| `si:remember [text]` | 즉시 기억 저장 |

## Agent Delegation (Task Queue System)

에이전트에 작업을 위임하고 자동 실행하는 시스템.

### Flow
```
사용자 지시 → 도메인 판별 → task-queue 등록 → dispatch-now.sh → agent-loop → Claude CLI
→ 완료 → review 상태 → 알림 → 사용자 리뷰 → task-approve.py → completed
```

### Task Queue Format
```json
{
  "version": 1,
  "project": "trading",
  "tasks": [
    {
      "id": "T001",
      "task": "L1 IC measurement for RSI divergence",
      "agent": "research-runner",
      "status": "pending",
      "depends_on": null
    }
  ]
}
```

### Commands
```bash
# 즉시 위임
dispatch-now.sh trading T001

# 태스크 승인
task-approve.py task-queue-trading.json T001 "검증 완료"
```

### Task Rules
- 1 task = 5분 이내 완료 가능 크기
- 1 task = 1파일 수정 또는 1함수 작성
- 대상 파일 경로 + 구체적 변경 내용 필수
- `dispatch_count >= 3` → blocked (수동 확인 필요)

## Telegram / Discord Notifications

### Setup
```bash
# brain-os.env 편집
TELEGRAM_BOT_TOKEN="your-bot-token"
TELEGRAM_CHAT_ID="your-chat-id"
# 또는
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

### Telegram Bot 만들기
1. @BotFather에게 `/newbot` 명령
2. 봇 이름 + 유저네임 설정
3. 받은 토큰을 `brain-os.env`에 입력
4. 봇에게 아무 메시지 전송
5. `https://api.telegram.org/bot<TOKEN>/getUpdates` 에서 chat_id 확인

### 알림이 오는 경우
- 태스크 리뷰 대기
- 태스크 실행 실패
- CLAUDE.md 무결성 위반
- Stale 패턴 정리
- Skill 승격 후보 발견

### 파일 전송
```bash
send-telegram.py --file /path/to/file.md general
```

## Customization

### Adding Domain Agents
`skills/` 디렉토리에 새 도메인 폴더 + SKILL.md 추가:
```
skills/
├── my-domain/
│   └── SKILL.md
```

### Adding Patterns
자동 감지 외에 수동으로도 추가 가능:
```
si:remember "이 프로젝트에서는 항상 X를 먼저 확인해야 한다"
```

### Task Queue System (Optional)
에이전트 위임 시스템을 쓰려면:
```
task-queue-{domain}.json → dispatch-now.sh → agent-loop-{domain}.sh
```

## Philosophy

1. **저장보다 이해** — 데이터를 모으는 게 아니라 사용자를 이해하는 것
2. **검색보다 구조화** — 필요할 때 찾는 게 아니라 이미 정리되어 있는 것
3. **기록보다 재사용** — 한 번 배운 건 다음에 바로 쓸 수 있는 것
4. **수동보다 자동** — 사람이 기억하라고 하지 않아도 시스템이 알아서 기억하는 것
5. **고정보다 진화** — 시스템이 점점 더 사용자 맞춤형으로 성장하는 것

## License

MIT

## Credits

Built by [@Kokoko9494](https://github.com/Kokoko9494) with Claude Code Max.
