#!/usr/bin/env python3
"""
Auto-Evolve — 완전 자동 학습 루프
수동 단계 없이 패턴 → 규칙 승격 + 스킬 생성 + 메모리 갱신

1. hits >= 3 candidate 패턴 → rules/ 자동 승격
2. 승격된 workflow/preference 패턴 → skills/ 자동 생성
3. user-model.json → MEMORY.md 자동 동기화
4. 알림 (텔레그램)

사용법: auto-evolve.py [--dry-run]
"""
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

BRAIN_DIR = Path(os.environ.get("BRAIN_OS_DIR", str(Path.home() / ".hermes")))
PATTERNS_DIR = BRAIN_DIR / "vault" / "patterns"
RULES_DIR = BRAIN_DIR / "rules"
SKILLS_DIR = BRAIN_DIR / "skills"
MEMORY_MD = BRAIN_DIR / "MEMORY.md"
USER_MODEL = BRAIN_DIR / "user-model.json"
LOG = BRAIN_DIR / "scripts" / "auto-evolve.log"

PROMOTE_THRESHOLD = 3
DRY_RUN = "--dry-run" in sys.argv

TELEGRAM_SCRIPT = Path.home() / ".openclaw" / "workspace" / "scripts" / "send_telegram.py"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if not DRY_RUN:
        with LOG.open("a") as f:
            f.write(line + "\n")


def notify(msg):
    if TELEGRAM_SCRIPT.exists() and not DRY_RUN:
        import subprocess
        subprocess.run(
            [sys.executable, str(TELEGRAM_SCRIPT), msg, "general"],
            timeout=10, capture_output=True
        )


def parse_pattern(path):
    """패턴 파일 파싱."""
    text = path.read_text(encoding="utf-8")
    meta = {}
    for key in ["category", "status", "hits", "created"]:
        m = re.search(rf"{key}:\s*(.+)", text)
        if m:
            val = m.group(1).strip()
            meta[key] = int(val) if key == "hits" else val

    # 본문 (--- 이후)
    parts = text.split("---")
    body = parts[-1].strip() if len(parts) >= 3 else text
    meta["body"] = body
    meta["path"] = path
    meta["name"] = path.stem
    return meta


# ── 1. 패턴 → rules 자동 승격 ──────────────────

def auto_promote():
    """hits >= 3 candidate → rules/ 승격."""
    promoted = []

    for f in PATTERNS_DIR.glob("*.md"):
        meta = parse_pattern(f)
        if meta.get("status") != "candidate":
            continue
        if meta.get("hits", 0) < PROMOTE_THRESHOLD:
            continue

        category = meta.get("category", "general")
        body = meta.get("body", "")
        name = meta["name"]

        # 적절한 rules 파일 결정
        rules_map = {
            "correction": "self-improving.md",
            "preference": "user.md",
            "workflow": "core.md",
            "insight": "self-improving.md",
            "error-fix": "self-improving.md",
        }
        target_rule = rules_map.get(category, "core.md")
        target_path = RULES_DIR / target_rule

        if not DRY_RUN:
            # rules 파일에 추가
            if target_path.exists():
                existing = target_path.read_text(encoding="utf-8")
            else:
                existing = f"# {target_rule.replace('.md', '').title()}\n\n"

            # 중복 체크
            if name in existing:
                log(f"  skip (already in rules): {name}")
                continue

            section = f"\n### {name} (auto-promoted {datetime.now().strftime('%Y-%m-%d')})\n{body}\n"
            target_path.write_text(existing + section, encoding="utf-8")

            # 원본 status 변경
            old_text = f.read_text(encoding="utf-8")
            new_text = old_text.replace("status: candidate", f"status: promoted\npromoted_to: rules/{target_rule}")
            f.write_text(new_text, encoding="utf-8")

        promoted.append(f"{name} → rules/{target_rule}")
        log(f"  promoted: {name} → {target_rule}")

    return promoted


# ── 2. 승격된 패턴 → skill 자동 생성 ──────────────────

def auto_create_skills():
    """workflow/preference 승격 패턴 → skills/ SKILL.md 생성."""
    created = []

    for f in PATTERNS_DIR.glob("*.md"):
        meta = parse_pattern(f)
        if meta.get("status") not in ("promoted",):
            continue
        if meta.get("category") not in ("workflow", "preference", "correction"):
            continue

        name = meta["name"]
        body = meta.get("body", "")

        # 이미 skill이 있는지 확인
        skill_dir = SKILLS_DIR / name
        if skill_dir.exists():
            continue

        if not DRY_RUN:
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(f"""---
name: {name}
description: Auto-generated from pattern — {meta.get('category', 'general')}
version: 1.0.0
auto_generated: true
source_pattern: {f.name}
created: {datetime.now().strftime('%Y-%m-%d')}
---

# {name}

{body}

## Usage
This skill was automatically extracted from a recurring pattern.
Apply when similar situations arise.
""", encoding="utf-8")

        created.append(name)
        log(f"  skill created: {name}")

    return created


# ── 3. user-model.json → MEMORY.md 자동 동기화 ──────────────────

def auto_sync_memory():
    """user-model.json의 분석 결과를 MEMORY.md에 반영."""
    if not USER_MODEL.exists():
        return False

    model = json.loads(USER_MODEL.read_text(encoding="utf-8"))
    topics = model.get("topic_frequency", {})
    style = model.get("communication_style", {})
    recurring = model.get("recurring_patterns", [])
    sessions = model.get("sessions_analyzed", 0)

    if not MEMORY_MD.exists():
        return False

    existing = MEMORY_MD.read_text(encoding="utf-8")

    # 자동 분석 섹션 갱신
    auto_section = f"""
## 자동 분석 (auto-evolve, {datetime.now().strftime('%Y-%m-%d %H:%M')})

### 관심사 빈도 (누적 {sessions} 세션)
"""
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        auto_section += f"- {topic}: {count}회\n"

    auto_section += f"""
### 소통 스타일
- 평균 메시지 길이: {style.get('avg_message_length', 0)}자
- 한국어 비율: {style.get('korean_ratio', 0) * 100:.0f}%
- 교정률: {style.get('correction_rate', 0) * 100:.1f}%
"""

    if recurring:
        auto_section += "\n### 반복 교정 패턴\n"
        for p in recurring:
            auto_section += f"- `{p['pattern']}` — {p['count']}회 ({p['status']})\n"

    if not DRY_RUN:
        # 기존 자동 분석 섹션 교체 또는 추가
        marker = "## 자동 분석 (auto-evolve"
        if marker in existing:
            # 기존 섹션 교체
            before = existing[:existing.index(marker)]
            # 다음 ## 찾기
            rest = existing[existing.index(marker):]
            next_section = rest.find("\n## ", 1)
            if next_section > 0:
                after = rest[next_section:]
            else:
                after = ""
            new_content = before.rstrip() + "\n" + auto_section + after
        else:
            new_content = existing.rstrip() + "\n" + auto_section

        MEMORY_MD.write_text(new_content, encoding="utf-8")

    log(f"  MEMORY.md synced (topics: {len(topics)}, sessions: {sessions})")
    return True


# ── Main ──────────────────

def main():
    log("=== auto-evolve start ===")
    if DRY_RUN:
        log("(dry-run mode)")

    # 1. 승격
    promoted = auto_promote()
    log(f"promoted: {len(promoted)}")

    # 2. skill 생성
    skills = auto_create_skills()
    log(f"skills created: {len(skills)}")

    # 3. 메모리 동기화
    synced = auto_sync_memory()
    log(f"memory synced: {synced}")

    # 4. 알림
    if promoted or skills:
        msg = f"🧠 [Auto-Evolve]\n"
        if promoted:
            msg += f"Promoted {len(promoted)} patterns:\n" + "\n".join(f"  • {p}" for p in promoted) + "\n"
        if skills:
            msg += f"Created {len(skills)} skills:\n" + "\n".join(f"  • {s}" for s in skills) + "\n"
        notify(msg)

    log("=== auto-evolve done ===")


if __name__ == "__main__":
    main()
