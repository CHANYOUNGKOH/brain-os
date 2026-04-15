#!/usr/bin/env python3
"""
Local User Understanding Engine — Honcho 대체
대화 transcript를 분석해서 사용자 모델을 업데이트한다.
무료, 외부 API 없음.

분석 대상:
- 교정 패턴 (부정어: 안돼, 하지마, 왜, 아닌데)
- 관심사 변화 (새 주제 등장 빈도)
- 반복 선호 (동일 요청 패턴)
- 판단 기준 (GO/KILL, 승인/거부 근거)
- 소통 스타일 변화

출력:
- ~/.hermes/user-model.json (구조화된 사용자 모델)
- MEMORY.md 갱신 제안
- Holographic에 핵심 사실 저장

사용법: user-model-update.py [session-jsonl-path]
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

import os
BRAIN_DIR = Path(os.environ.get("BRAIN_OS_DIR", str(Path.home() / ".brain-os")))
MODEL_PATH = BRAIN_DIR / "user-model.json"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"

# 교정 신호 패턴
CORRECTION_PATTERNS = [
    r"안돼", r"하지마", r"하지 마", r"거기 아님", r"아닌데", r"그거 아니고",
    r"잘못", r"왜 .+했어", r"왜 .+보냈", r"왜 .+보내", r"아님\?",
    r"그렇게 하지", r"싫어", r"필요없", r"필요 없",
]

# 승인 신호
APPROVAL_PATTERNS = [
    r"^ㅇㅇ$", r"^ㄱㄱ", r"^둘다", r"^좋아", r"^오케이", r"^ㅇㅋ",
    r"^진행", r"^해봐", r"^해줘",
]

# 관심사 키워드
TOPIC_KEYWORDS = {
    "trading": ["시그널", "백테스트", "매매", "sharpe", "IC", "피처", "L1", "L2", "L3", "BTC", "ETH"],
    "content": ["콘텐츠", "브랜드", "PT", "2bass", "fasting", "마케팅"],
    "infra": ["크론", "cron", "모니터", "디스코드", "웹훅", "스크립트"],
    "agent": ["에이전트", "위임", "태스크", "dispatch", "자가학습", "패턴"],
    "memory": ["기억", "memory", "학습", "honcho", "holographic", "vault"],
}


def load_existing_model():
    if MODEL_PATH.exists():
        return json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "last_updated": None,
        "sessions_analyzed": 0,
        "corrections": [],
        "approvals": [],
        "topic_frequency": {},
        "communication_style": {
            "avg_message_length": 0,
            "korean_ratio": 0,
            "correction_rate": 0,
            "approval_rate": 0,
        },
        "preferences": [],
        "recurring_patterns": [],
    }


def find_latest_session():
    """가장 최근 세션 transcript 찾기."""
    for project_dir in CLAUDE_PROJECTS.iterdir():
        if not project_dir.is_dir():
            continue
        jsonl_files = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if jsonl_files:
            return jsonl_files[0]
    return None


def extract_user_messages(jsonl_path):
    """세션 transcript에서 사용자 메시지만 추출."""
    messages = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("type") == "user":
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str) and content.strip():
                        # metadata 제거
                        clean = re.sub(r'\[media attached:.*?\]', '', content)
                        clean = re.sub(r'Conversation info.*?```\n', '', clean, flags=re.DOTALL)
                        clean = re.sub(r'Sender.*?```\n', '', clean, flags=re.DOTALL)
                        clean = re.sub(r'<system-reminder>.*?</system-reminder>', '', clean, flags=re.DOTALL)
                        clean = clean.strip()
                        if clean and len(clean) > 1:
                            messages.append(clean)
            except (json.JSONDecodeError, KeyError):
                continue
    return messages


def analyze_corrections(messages):
    """교정 패턴 분석."""
    corrections = []
    for msg in messages:
        for pattern in CORRECTION_PATTERNS:
            if re.search(pattern, msg):
                corrections.append({
                    "message": msg[:100],
                    "pattern": pattern,
                    "timestamp": datetime.now().isoformat(),
                })
                break
    return corrections


def analyze_approvals(messages):
    """승인 패턴 분석."""
    approvals = []
    for msg in messages:
        for pattern in APPROVAL_PATTERNS:
            if re.search(pattern, msg.strip()):
                approvals.append({
                    "message": msg[:50],
                    "timestamp": datetime.now().isoformat(),
                })
                break
    return approvals


def analyze_topics(messages):
    """관심사 빈도 분석."""
    topic_count = Counter()
    for msg in messages:
        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in msg.lower():
                    topic_count[topic] += 1
                    break
    return dict(topic_count)


def analyze_communication_style(messages):
    """소통 스타일 분석."""
    if not messages:
        return {}

    lengths = [len(m) for m in messages]
    korean_msgs = sum(1 for m in messages if re.search(r"[가-힣]", m))

    corrections = sum(1 for m in messages
                      for p in CORRECTION_PATTERNS if re.search(p, m))
    approvals = sum(1 for m in messages
                    for p in APPROVAL_PATTERNS if re.search(p, m.strip()))

    return {
        "avg_message_length": round(sum(lengths) / len(lengths), 1),
        "korean_ratio": round(korean_msgs / len(messages), 2),
        "correction_rate": round(corrections / len(messages), 3),
        "approval_rate": round(approvals / len(messages), 3),
        "total_messages": len(messages),
    }


def detect_recurring_patterns(model, new_corrections):
    """반복 교정 패턴 감지."""
    all_corrections = model.get("corrections", []) + new_corrections
    pattern_count = Counter(c["pattern"] for c in all_corrections)
    recurring = [
        {"pattern": p, "count": c, "status": "recurring" if c >= 3 else "emerging"}
        for p, c in pattern_count.most_common(10) if c >= 2
    ]
    return recurring


def update_model(model, messages, session_path):
    """사용자 모델 업데이트."""
    new_corrections = analyze_corrections(messages)
    new_approvals = analyze_approvals(messages)
    topic_freq = analyze_topics(messages)
    comm_style = analyze_communication_style(messages)

    # 누적
    model["corrections"].extend(new_corrections)
    model["approvals"].extend(new_approvals)

    # 토픽 빈도 누적
    for topic, count in topic_freq.items():
        model["topic_frequency"][topic] = model["topic_frequency"].get(topic, 0) + count

    # 소통 스타일 (최신으로 덮어쓰기)
    model["communication_style"] = comm_style

    # 반복 패턴 감지
    model["recurring_patterns"] = detect_recurring_patterns(model, [])

    # 메타데이터
    model["sessions_analyzed"] += 1
    model["last_updated"] = datetime.now().isoformat()
    model["last_session"] = str(session_path)

    # 최근 100건만 유지
    model["corrections"] = model["corrections"][-100:]
    model["approvals"] = model["approvals"][-100:]

    return model


def save_model(model):
    MODEL_PATH.write_text(
        json.dumps(model, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[user-model] saved: {MODEL_PATH}")


def print_summary(model, new_corrections, new_approvals, topic_freq):
    print(f"\n[user-model] === Session Analysis ===")
    print(f"  Sessions analyzed: {model['sessions_analyzed']}")
    print(f"  New corrections: {len(new_corrections)}")
    print(f"  New approvals: {len(new_approvals)}")
    print(f"  Topic distribution: {topic_freq}")
    print(f"  Communication style: {json.dumps(model['communication_style'], ensure_ascii=False)}")
    if model["recurring_patterns"]:
        print(f"  Recurring patterns: {model['recurring_patterns']}")


def main():
    # 세션 경로
    if len(sys.argv) > 1:
        session_path = Path(sys.argv[1])
    else:
        session_path = find_latest_session()
        if not session_path:
            print("[user-model] no session found")
            return

    print(f"[user-model] analyzing: {session_path.name}")

    # 메시지 추출
    messages = extract_user_messages(session_path)
    print(f"[user-model] {len(messages)} user messages extracted")

    if not messages:
        print("[user-model] no messages, skip")
        return

    # 모델 로드 + 업데이트
    model = load_existing_model()
    new_corrections = analyze_corrections(messages)
    new_approvals = analyze_approvals(messages)
    topic_freq = analyze_topics(messages)

    model = update_model(model, messages, session_path)
    save_model(model)
    print_summary(model, new_corrections, new_approvals, topic_freq)


if __name__ == "__main__":
    main()
