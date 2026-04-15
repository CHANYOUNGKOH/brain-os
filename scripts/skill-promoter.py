#!/usr/bin/env python3
"""
Skill Auto-Promoter — 성공 패턴 → skill 후보 자동 감지
무료, 외부 API 없음.

동작:
1. vault/patterns/ 스캔
2. hits >= 3 + status=candidate → skill 승격 후보로 마킹
3. 완료된 태스크에서 반복 성공 패턴 감지
4. 알림 생성 (텔레그램 또는 stdout)

사용법: skill-promoter.py [--notify]
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

VAULT_PATTERNS = Path.home() / ".hermes" / "vault" / "patterns"
SKILLS_DIR = Path.home() / ".hermes" / "skills"
TASK_QUEUES = [
    Path.home() / ".openclaw" / "workspace" / "task-queue-trading.json",
    Path.home() / ".openclaw" / "workspace" / "task-queue-content.json",
    Path.home() / ".openclaw" / "workspace" / "task-queue-infra.json",
]

PROMOTE_THRESHOLD = 3  # hits >= 3 → promote candidate
SEND_TELEGRAM = Path.home() / ".openclaw" / "workspace" / "scripts" / "send_telegram.py"


def scan_patterns():
    """vault/patterns/ 스캔, 승격 후보 찾기."""
    candidates = []
    promoted = []
    stale = []

    if not VAULT_PATTERNS.exists():
        return candidates, promoted, stale

    for f in VAULT_PATTERNS.glob("*.md"):
        content = f.read_text(encoding="utf-8")

        # YAML frontmatter 파싱
        hits = 0
        status = "candidate"
        category = ""

        hits_match = re.search(r"hits:\s*(\d+)", content)
        if hits_match:
            hits = int(hits_match.group(1))

        status_match = re.search(r"status:\s*(\S+)", content)
        if status_match:
            status = status_match.group(1)

        cat_match = re.search(r"category:\s*(\S+)", content)
        if cat_match:
            category = cat_match.group(1)

        entry = {
            "file": f.name,
            "hits": hits,
            "status": status,
            "category": category,
        }

        if status == "promoted":
            promoted.append(entry)
        elif status == "candidate" and hits >= PROMOTE_THRESHOLD:
            candidates.append(entry)
        elif status in ("stale", "archived"):
            stale.append(entry)

    return candidates, promoted, stale


def scan_completed_tasks():
    """완료된 태스크에서 반복 성공 패턴 감지."""
    success_patterns = {}

    for queue_path in TASK_QUEUES:
        if not queue_path.exists():
            continue
        try:
            data = json.loads(queue_path.read_text(encoding="utf-8"))
            tasks = data.get("tasks", [])
            completed = [t for t in tasks if t.get("status") == "completed"]

            for task in completed:
                # 태스크 설명에서 패턴 추출
                desc = task.get("description", task.get("task", ""))
                # L1, L2, L3 등 반복 키워드
                for keyword in ["L1", "L2", "L3", "IC 측정", "백테스트", "5m 검증"]:
                    if keyword in desc:
                        key = f"task-pattern:{keyword}"
                        success_patterns[key] = success_patterns.get(key, 0) + 1
        except (json.JSONDecodeError, KeyError):
            continue

    # 3회 이상 반복된 성공 패턴
    return {k: v for k, v in success_patterns.items() if v >= PROMOTE_THRESHOLD}


def generate_report(candidates, promoted, stale, task_patterns):
    """승격 보고서 생성."""
    lines = [
        f"📊 Skill Promoter Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"Promoted: {len(promoted)} | Candidates: {len(candidates)} | Stale: {len(stale)}",
    ]

    if candidates:
        lines.append(f"\n🔺 승격 후보 (hits >= {PROMOTE_THRESHOLD}):")
        for c in candidates:
            lines.append(f"  - {c['file']} (hits:{c['hits']}, cat:{c['category']})")

    if task_patterns:
        lines.append(f"\n🔄 반복 성공 태스크 패턴:")
        for pattern, count in task_patterns.items():
            lines.append(f"  - {pattern}: {count}회")

    if not candidates and not task_patterns:
        lines.append("\n✅ 승격 후보 없음")

    return "\n".join(lines)


def notify_telegram(report):
    """텔레그램으로 알림."""
    if SEND_TELEGRAM.exists():
        import subprocess
        subprocess.run(
            [sys.executable, str(SEND_TELEGRAM), report, "general"],
            timeout=10,
            capture_output=True,
        )


def main():
    notify = "--notify" in sys.argv

    candidates, promoted, stale, = scan_patterns()
    task_patterns = scan_completed_tasks()
    report = generate_report(candidates, promoted, stale, task_patterns)

    print(report)

    if notify and (candidates or task_patterns):
        notify_telegram(report)
        print("\n[skill-promoter] telegram notification sent")


if __name__ == "__main__":
    main()
