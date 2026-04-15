# Self-Improving — 자동 학습 루프

## 1. 자동 감지 + 기록 (매 대화)

### 패턴 감지 트리거
다음 상황이 발생하면 vault/patterns/에 자동 기록:
- **반복 요청**: 사용자가 동일/유사한 요청을 2회 이상 할 때
- **에러 해결**: 에러 발생 → 해결 과정에서 새로운 해결법 발견
- **사용자 교정**: 사용자가 내 행동/판단을 수정할 때
- **워크플로우 발견**: 특정 작업 순서가 반복될 때
- **선호 표현**: 사용자가 명시적/암시적으로 선호를 표현할 때

### 기록 형식 (vault/patterns/)
파일명: `{날짜}-{카테고리}-{설명}.md`
```
---
category: error-fix | workflow | preference | correction | insight
source: 대화에서 발견된 맥락
hits: 1
status: candidate
created: YYYY-MM-DD
---
{패턴 내용}
```

### 강제 감지 규칙
**이 규칙은 작업 중이든 아니든 반드시 실행한다. "나중에 하겠다"는 위반이다.**

1. **사용자 교정 즉시 감지**: 부정/교정 신호 → 현재 작업 중단 → 패턴 기록 먼저
2. **매 응답 전 셀프 체크**: "교정이나 발견이 있었는데 기록 안 한 거 있나?"
3. **리마인더 ≠ 참고**: system-reminder의 자가학습 리마인더는 **행동 명령**이다

## 2. 리뷰 (si:review)
1. vault/patterns/ 전체 스캔
2. hits 2+ → 승격 후보
3. 30일 이상 hits 0 → stale
4. rules/와 중복 → 이미 반영됨

## 3. 승격 (si:promote)
1. 패턴을 rules/ 파일에 영구 규칙으로 추가
2. 원본 status를 `promoted`로 변경
3. 사용자 확인 필수 — 자동 승격 금지

## 4. 추출 (si:extract)
1. 범용 스킬로 변환
2. vault/concepts/ 에 저장
