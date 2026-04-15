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
├── scripts/ (자동화)
│   ├── capture-history.py   — 브라우저 히스토리 수집
│   ├── user-model-update.py — 사용자 이해 엔진
│   ├── auto-memorize.py     — 대화→사실 자동 추출
│   ├── skill-promoter.py    — 성공 패턴→skill 승격
│   └── vault-hygiene.sh     — stale 정리 + 무결성
├── skills/ (도메인 스킬)
└── memory/ (세션 기록)
```

## Quick Start

### 1. Requirements
- macOS / Linux
- Claude Code Max subscription ($100/mo or $200/mo)
- Python 3.9+
- Git

### 2. Install
```bash
git clone https://github.com/Kokoko9494/brain-os.git ~/.brain-os
cd ~/.brain-os
./install.sh
```

### 3. What install.sh does
1. 디렉토리 구조 생성 (vault, rules, skills, memory, scripts)
2. CLAUDE.md 템플릿 생성
3. Claude Code hooks 설정 (자가학습 리마인더)
4. Cron jobs 등록 (캡처, 분석, 정리)
5. 초기 규칙 파일 생성

### 4. Start using
```bash
cd ~/.brain-os
# Claude Code가 CLAUDE.md를 자동 로드
# 대화하면서 자동으로 학습 시작
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
