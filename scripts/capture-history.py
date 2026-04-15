#!/usr/bin/env python3
"""
Browser History Capture — Chrome + Safari 로컬 히스토리 수집
무료, 외부 API 없음. 로컬 SQLite DB 직접 읽기.

사용법: capture-history.py [YYYY-MM-DD]
기본: 어제 날짜
"""
import sqlite3
import shutil
import tempfile
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

import platform

BRAIN_DIR = Path(os.environ.get("BRAIN_OS_DIR", str(Path.home() / ".brain-os")))
VAULT = BRAIN_DIR / "vault"
RAW_DIR = VAULT / "raw"
LOG_FILE = VAULT / "log.md"

# 플랫폼별 Chrome 경로
if platform.system() == "Windows":
    CHROME_HISTORY = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Default" / "History"
    SAFARI_HISTORY = None  # Safari 없음
elif platform.system() == "Darwin":
    CHROME_HISTORY = Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "History"
    SAFARI_HISTORY = Path.home() / "Library" / "Safari" / "History.db"
else:  # Linux
    CHROME_HISTORY = Path.home() / ".config" / "google-chrome" / "Default" / "History"
    SAFARI_HISTORY = None

# Perplexity 등 보존 가치 높은 도메인
HIGH_VALUE_DOMAINS = [
    "perplexity.ai",
    "chatgpt.com",
    "claude.ai",
    "github.com",
    "stackoverflow.com",
    "arxiv.org",
    "docs.google.com",
]

# 무시할 도메인
IGNORE_DOMAINS = [
    "google.com/search",
    "youtube.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "reddit.com",
    "mail.google.com",
    "accounts.google.com",
    "chrome://",
    "about:",
    "localhost",
    "127.0.0.1",
    "/oauth/",
    "/login/",
    "/auth/",
    "/callback",
    "/authorize",
    "/signup",
    "/verify/",
    "/redirect",
    "accounts.",
    "login.",
    "auth.",
]


def get_target_date(arg=None):
    if arg:
        return datetime.strptime(arg, "%Y-%m-%d").date()
    return (datetime.now() - timedelta(days=1)).date()


def copy_db(src):
    """Chrome은 락이 걸려있으므로 복사해서 읽는다."""
    if not src.exists():
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    shutil.copy2(src, tmp.name)
    # WAL 파일도 복사
    wal = Path(str(src) + "-wal")
    if wal.exists():
        shutil.copy2(wal, tmp.name + "-wal")
    return tmp.name


def fetch_chrome(target_date):
    """Chrome History SQLite에서 특정 날짜 방문 기록 추출."""
    db_path = copy_db(CHROME_HISTORY)
    if not db_path:
        return []

    # Chrome timestamp: microseconds since 1601-01-01
    epoch_start = datetime(1601, 1, 1)
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    chrome_start = int((day_start - epoch_start).total_seconds() * 1_000_000)
    chrome_end = int((day_end - epoch_start).total_seconds() * 1_000_000)

    results = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("""
            SELECT DISTINCT u.url, u.title, v.visit_time
            FROM urls u
            JOIN visits v ON u.id = v.url
            WHERE v.visit_time >= ? AND v.visit_time < ?
            ORDER BY v.visit_time
        """, (chrome_start, chrome_end))

        for url, title, visit_time in cursor:
            results.append({
                "source": "chrome",
                "url": url,
                "title": title or "",
                "timestamp": str(day_start + timedelta(
                    microseconds=visit_time - chrome_start
                ))[:19],
            })
        conn.close()
    except Exception as e:
        print(f"[chrome] error: {e}", file=sys.stderr)
    finally:
        os.unlink(db_path)
        wal_tmp = db_path + "-wal"
        if os.path.exists(wal_tmp):
            os.unlink(wal_tmp)

    return results


def fetch_safari(target_date):
    """Safari History.db에서 특정 날짜 방문 기록 추출."""
    db_path = copy_db(SAFARI_HISTORY)
    if not db_path:
        return []

    # Safari timestamp: seconds since 2001-01-01
    safari_epoch = datetime(2001, 1, 1)
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    safari_start = (day_start - safari_epoch).total_seconds()
    safari_end = (day_end - safari_epoch).total_seconds()

    results = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("""
            SELECT DISTINCT hi.url, hv.title, hv.visit_time
            FROM history_items hi
            JOIN history_visits hv ON hi.id = hv.history_item
            WHERE hv.visit_time >= ? AND hv.visit_time < ?
            ORDER BY hv.visit_time
        """, (safari_start, safari_end))

        for url, title, visit_time in cursor:
            results.append({
                "source": "safari",
                "url": url,
                "title": title or "",
                "timestamp": str(safari_epoch + timedelta(seconds=visit_time))[:19],
            })
        conn.close()
    except Exception as e:
        print(f"[safari] error: {e}", file=sys.stderr)
    finally:
        os.unlink(db_path)

    return results


def is_ignored(url):
    return any(d in url for d in IGNORE_DOMAINS)


def is_high_value(url):
    return any(d in url for d in HIGH_VALUE_DOMAINS)


def deduplicate(entries):
    """URL 기준 중복 제거, 첫 방문 유지."""
    seen = set()
    result = []
    for e in entries:
        url = e["url"].split("?")[0].split("#")[0]  # strip params
        if url not in seen:
            seen.add(url)
            result.append(e)
    return result


def save_raw(target_date, entries, high_value):
    """vault/raw/에 날짜별 히스토리 저장."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    date_str = target_date.strftime("%Y-%m-%d")

    # 전체 히스토리 요약
    output_path = RAW_DIR / f"history-{date_str}.md"
    lines = [
        f"---",
        f"type: browser-history",
        f"date: {date_str}",
        f"chrome_count: {sum(1 for e in entries if e['source'] == 'chrome')}",
        f"safari_count: {sum(1 for e in entries if e['source'] == 'safari')}",
        f"high_value_count: {len(high_value)}",
        f"---",
        f"",
        f"# Browser History — {date_str}",
        f"",
    ]

    if high_value:
        lines.append("## High-Value Pages")
        lines.append("")
        for e in high_value:
            lines.append(f"- [{e['title']}]({e['url']}) ({e['source']}, {e['timestamp']})")
        lines.append("")

    lines.append("## All Visits")
    lines.append("")
    for e in entries:
        marker = " ⭐" if is_high_value(e["url"]) else ""
        lines.append(f"- [{e['title'] or 'untitled'}]({e['url']}) ({e['source']}){marker}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[capture] saved: {output_path} ({len(entries)} entries, {len(high_value)} high-value)")
    return output_path


def update_log(target_date, entry_count, hv_count):
    """vault/log.md에 캡처 내역 추가."""
    date_str = target_date.strftime("%Y-%m-%d")
    log_line = f"- [{date_str}] capture-history: {entry_count} entries, {hv_count} high-value\n"

    if LOG_FILE.exists():
        content = LOG_FILE.read_text(encoding="utf-8")
        if date_str not in content:
            # 파일 끝에 추가
            with LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(log_line)
    else:
        LOG_FILE.write_text(f"# Vault Log\n\n{log_line}", encoding="utf-8")


def main():
    target_date = get_target_date(sys.argv[1] if len(sys.argv) > 1 else None)
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"[capture] target date: {date_str}")

    # 수집
    chrome = fetch_chrome(target_date)
    try:
        safari = fetch_safari(target_date)
    except Exception as e:
        print(f"[capture] safari skipped (permission): {e}", file=sys.stderr)
        safari = []
    print(f"[capture] chrome: {len(chrome)}, safari: {len(safari)}")

    # 필터 + 중복제거
    all_entries = chrome + safari
    filtered = [e for e in all_entries if not is_ignored(e["url"])]
    deduped = deduplicate(filtered)
    high_value = [e for e in deduped if is_high_value(e["url"])]

    if not deduped:
        print(f"[capture] {date_str} — no entries after filtering, skip")
        return

    # 저장
    save_raw(target_date, deduped, high_value)
    update_log(target_date, len(deduped), len(high_value))

    # high-value URLs을 JSON으로 출력 (후속 파이프라인용)
    if high_value:
        hv_path = RAW_DIR / f"high-value-{date_str}.json"
        hv_path.write_text(json.dumps(high_value, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[capture] high-value saved: {hv_path}")


if __name__ == "__main__":
    main()
