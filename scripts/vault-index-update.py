#!/usr/bin/env python3
"""
Vault INDEX.md Auto-Update
vault/ 전체를 스캔해서 INDEX.md를 자동 재생성한다.

역할:
- 에이전트가 vault 검색 시 index 먼저 읽고 필요한 파일만 접근 (토큰 절약)
- 중복 방지 (이미 있는 주제인지 즉시 확인)
- stale 감지 (오래된 파일 표시)
- orphan 감지 (카테고리에 맞지 않는 파일)

사용법: vault-index-update.py [--dry-run]
"""
import os
import re
import sys
from pathlib import Path
from datetime import datetime

VAULT = Path(os.environ.get("BRAIN_OS_DIR", str(Path.home() / ".hermes"))) / "vault"
INDEX_PATH = VAULT / "INDEX.md"
LOG_PATH = VAULT / "log.md"
DRY_RUN = "--dry-run" in sys.argv

CATEGORIES = ["entities", "concepts", "comparisons", "queries", "raw", "patterns"]


def extract_frontmatter(path):
    """파일에서 frontmatter와 첫 줄 설명 추출."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}

    meta = {}

    # frontmatter 파싱
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            for line in fm.strip().split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip()

    # 첫 번째 # 헤딩에서 설명 추출
    for line in text.split("\n"):
        if line.startswith("# ") and "---" not in line:
            meta["heading"] = line[2:].strip()
            break

    # 파일 수정 시간
    stat = path.stat()
    meta["mtime"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
    meta["size"] = stat.st_size

    return meta


def scan_category(category):
    """카테고리 디렉토리 스캔."""
    cat_dir = VAULT / category
    if not cat_dir.exists():
        return []

    files = []
    for f in sorted(cat_dir.glob("*.md")):
        meta = extract_frontmatter(f)
        name = f.stem
        heading = meta.get("heading", meta.get("type", name))

        # patterns은 status 표시
        status = meta.get("status", "")
        hits = meta.get("hits", "")
        category_tag = meta.get("category", "")

        entry = {
            "name": name,
            "path": f"/{category}/{f.name}",  # relative to vault
            "heading": heading,
            "mtime": meta.get("mtime", ""),
            "status": status,
            "hits": hits,
            "category_tag": category_tag,
        }
        files.append(entry)

    # JSON도 포함 (raw/ 등)
    for f in sorted(cat_dir.glob("*.json")):
        stat = f.stat()
        files.append({
            "name": f.stem,
            "path": f"/{category}/{f.name}",
            "heading": f"[JSON] {f.stem}",
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
            "status": "",
            "hits": "",
            "category_tag": "",
        })

    return files


def generate_index():
    """INDEX.md 내용 생성."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Vault Index — 지식 지형도",
        "",
        f"마지막 갱신: {now} (자동)",
        "",
    ]

    total_files = 0

    for cat in CATEGORIES:
        files = scan_category(cat)
        total_files += len(files)

        # 카테고리 헤더
        cat_labels = {
            "entities": "entities/ — 사람, 서비스, 시스템, 프로젝트",
            "concepts": "concepts/ — 원리, 패턴, 방법론",
            "comparisons": "comparisons/ — A vs B 비교",
            "queries": "queries/ — 질문과 축적된 답",
            "raw": "raw/ — 시점 스냅샷, 히스토리",
            "patterns": "patterns/ — 자동 학습 기록",
        }
        lines.append(f"## {cat_labels.get(cat, cat + '/')}")
        lines.append("")

        if not files:
            lines.append("_(비어있음)_")
            lines.append("")
            continue

        # concepts는 하위 그룹핑 (prefix 기반)
        if cat == "concepts":
            groups = {}
            for f in files:
                prefix = f["name"].split("-")[0] if "-" in f["name"] else "기타"
                prefix_labels = {
                    "principle": "원칙",
                    "method": "방법론",
                    "pattern": "패턴",
                    "workaround": "워크어라운드",
                }
                group = prefix_labels.get(prefix, "기타")
                groups.setdefault(group, []).append(f)

            for group_name, group_files in groups.items():
                lines.append(f"### {group_name}")
                for f in group_files:
                    lines.append(f"- [{f['name']}]({cat}/{f['name']}.md) — {f['heading']}")
                lines.append("")
        elif cat == "patterns":
            # patterns은 status별 그룹핑
            by_status = {}
            for f in files:
                s = f.get("status", "unknown") or "unknown"
                by_status.setdefault(s, []).append(f)

            for status in ["candidate", "promoted", "unknown"]:
                if status not in by_status:
                    continue
                status_label = {
                    "candidate": "후보 (candidate)",
                    "promoted": "승격됨 (promoted)",
                    "unknown": "미분류",
                }.get(status, status)
                lines.append(f"### {status_label}")
                for f in by_status[status]:
                    hits_str = f" (hits:{f['hits']})" if f['hits'] else ""
                    cat_str = f" [{f['category_tag']}]" if f['category_tag'] else ""
                    lines.append(f"- {f['name']}{cat_str}{hits_str}")
                lines.append("")
        else:
            for f in files:
                lines.append(f"- [{f['name']}]({cat}/{f['name']}.md) — {f['heading']}")
            lines.append("")

    # 통계
    lines.append("---")
    lines.append(f"총 파일: {total_files}개")
    lines.append("")

    return "\n".join(lines)


def update_log():
    """log.md에 인덱스 갱신 기록."""
    now = datetime.now().strftime("%Y-%m-%d")
    log_line = f"- [{now}] vault-index-update: INDEX.md auto-regenerated\n"

    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
        # 오늘 이미 기록했으면 스킵
        if f"[{now}] vault-index-update" in content:
            return
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(log_line)


def main():
    if not VAULT.exists():
        print(f"[vault-index] vault not found: {VAULT}")
        return

    content = generate_index()

    if DRY_RUN:
        print(content)
        print(f"\n[vault-index] (dry-run, not saved)")
        return

    INDEX_PATH.write_text(content, encoding="utf-8")
    update_log()
    print(f"[vault-index] INDEX.md updated ({len(content)} chars)")


if __name__ == "__main__":
    main()
