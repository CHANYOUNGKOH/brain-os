#!/usr/bin/env python3
"""
Holographic Auto-Accumulation — 대화에서 자동으로 사실 추출 + 저장
무료, 외부 API 없음. 로컬 키워드 기반 추출.

대화 transcript에서 핵심 사실/결정을 추출해서 Holographic MemoryStore에 저장.

추출 대상:
- 사용자 결정 (확정, 결정, 쓰자, 하자)
- 규칙 설정 (금지, 필수, 반드시, 강제)
- 사실 발견 (실은, 알고보니, 원인은, 이유는)
- 에러 해결 (해결, 고침, 수정, fix)

사용법: auto-memorize.py [session-jsonl-path]
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

import os
BRAIN_DIR = Path(os.environ.get("BRAIN_OS_DIR", str(Path.home() / ".brain-os")))
HOLOGRAPHIC_DB = BRAIN_DIR / "holographic.db"
PLUGIN_PATH = BRAIN_DIR / "holographic"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"

# 추출 패턴 (assistant 메시지에서)
FACT_PATTERNS = {
    "decision": [
        r"확정[):]", r"결정[):]", r"확인 완료", r"승격 완료",
        r"으로 (결정|확정|변경)", r"KILL", r"GO 판정",
    ],
    "rule": [
        r"금지", r"필수", r"반드시", r"강제", r"HARD BLOCK",
        r"위반", r"스킵 금지",
    ],
    "discovery": [
        r"원인[은:]", r"이유[는:]", r"알고.?보니", r"실은",
        r"문제[는:]", r"갭[은:]",
    ],
    "resolution": [
        r"해결[:]", r"수정 완료", r"고침", r"fix",
        r"작동 확인", r"✅",
    ],
}


def find_latest_session():
    for project_dir in CLAUDE_PROJECTS.iterdir():
        if not project_dir.is_dir():
            continue
        jsonl_files = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if jsonl_files:
            return jsonl_files[0]
    return None


def extract_facts(jsonl_path):
    """assistant 메시지에서 핵심 사실 추출."""
    facts = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                # assistant 메시지만
                if entry.get("type") != "assistant":
                    continue
                msg = entry.get("message", {})
                content_parts = msg.get("content", [])
                if isinstance(content_parts, str):
                    text = content_parts
                elif isinstance(content_parts, list):
                    text = " ".join(
                        p.get("text", "") for p in content_parts
                        if isinstance(p, dict) and p.get("type") == "text"
                    )
                else:
                    continue

                if not text or len(text) < 10:
                    continue

                # 문장 단위로 분리
                sentences = re.split(r'[.。\n]', text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 10 or len(sentence) > 200:
                        continue

                    for category, patterns in FACT_PATTERNS.items():
                        for pattern in patterns:
                            if re.search(pattern, sentence):
                                facts.append({
                                    "content": sentence,
                                    "category": category,
                                })
                                break
                        else:
                            continue
                        break
            except (json.JSONDecodeError, KeyError):
                continue

    return facts


def deduplicate_facts(facts):
    """유사 사실 제거."""
    seen = set()
    unique = []
    for fact in facts:
        key = fact["content"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(fact)
    return unique


def store_facts(facts):
    """Holographic MemoryStore에 저장."""
    sys.path.insert(0, str(PLUGIN_PATH))
    from store import MemoryStore

    store = MemoryStore(str(HOLOGRAPHIC_DB))
    stored = 0
    skipped = 0

    for fact in facts:
        try:
            store.add_fact(fact["content"], category=fact["category"])
            stored += 1
        except Exception:
            skipped += 1

    store.close()
    return stored, skipped


def main():
    if len(sys.argv) > 1:
        session_path = Path(sys.argv[1])
    else:
        session_path = find_latest_session()
        if not session_path:
            print("[auto-memorize] no session found")
            return

    print(f"[auto-memorize] analyzing: {session_path.name}")

    facts = extract_facts(session_path)
    print(f"[auto-memorize] {len(facts)} raw facts extracted")

    facts = deduplicate_facts(facts)
    print(f"[auto-memorize] {len(facts)} unique facts after dedup")

    if not facts:
        print("[auto-memorize] no facts to store")
        return

    stored, skipped = store_facts(facts)
    print(f"[auto-memorize] stored: {stored}, skipped (duplicate): {skipped}")

    # 카테고리별 요약
    from collections import Counter
    cats = Counter(f["category"] for f in facts)
    print(f"[auto-memorize] categories: {dict(cats)}")


if __name__ == "__main__":
    main()
