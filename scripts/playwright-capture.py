#!/usr/bin/env python3
"""
Playwright Accessibility Tree Capture
high-value URL을 Playwright로 접속 → accessibility tree 추출 → vault/raw/ 저장

스크린샷 대신 a11y tree 사용:
- 토큰 비용 최소 (텍스트 기반)
- OCR 불필요
- 구조화된 콘텐츠 바로 사용 가능

사용법:
  playwright-capture.py                     # 어제 high-value URLs 캡처
  playwright-capture.py 2026-04-14          # 특정 날짜
  playwright-capture.py --url https://...   # 단일 URL 캡처
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

VAULT = Path.home() / ".hermes" / "vault"
RAW_DIR = VAULT / "raw"
LOG_FILE = VAULT / "log.md"

# 캡처 제외 도메인 (로그인 필수 / 캡처 불가)
SKIP_DOMAINS = [
    "claude.ai",      # 로그인 세션 필수
    "chatgpt.com",    # 로그인 세션 필수
]

# 최대 캡처 페이지 수 (한 번 실행당)
MAX_PAGES = 10

# 페이지 로드 대기 (ms)
WAIT_MS = 3000


def get_high_value_urls(date_str):
    """high-value JSON에서 URL 목록 가져오기."""
    hv_path = RAW_DIR / f"high-value-{date_str}.json"
    if not hv_path.exists():
        print(f"[playwright] no high-value file for {date_str}")
        return []

    data = json.loads(hv_path.read_text(encoding="utf-8"))
    urls = []
    for entry in data:
        url = entry.get("url", "")
        if any(d in url for d in SKIP_DOMAINS):
            continue
        urls.append({
            "url": url,
            "title": entry.get("title", ""),
            "source": entry.get("source", ""),
        })
    return urls[:MAX_PAGES]


CAPTURE_SCRIPT = Path(__file__).parent / "capture-a11y.js"


def capture_with_script(url, timeout_ms=30000):
    """Node.js capture-a11y.js로 accessibility tree 캡처."""
    try:
        result = subprocess.run(
            ["node", str(CAPTURE_SCRIPT), url, str(timeout_ms)],
            capture_output=True, text=True, timeout=90,
            cwd=str(Path.home() / ".hermes"),  # node_modules 위치
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr:
            print(f"[playwright] stderr: {result.stderr[:200]}", file=sys.stderr)
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[playwright] error: {e}", file=sys.stderr)
        return None


def flatten_a11y_tree(node, depth=0):
    """accessibility tree를 읽기 좋은 텍스트로 변환."""
    if not node:
        return ""

    lines = []
    indent = "  " * depth
    role = node.get("role", "")
    name = node.get("name", "")
    value = node.get("value", "")

    # 의미 있는 노드만 출력
    if name or value:
        parts = [f"{indent}[{role}]"]
        if name:
            parts.append(name[:200])
        if value:
            parts.append(f"= {value[:200]}")
        lines.append(" ".join(parts))

    for child in node.get("children", []):
        lines.append(flatten_a11y_tree(child, depth + 1))

    return "\n".join(line for line in lines if line.strip())


def save_capture(date_str, url_info, a11y_text):
    """캡처 결과를 vault/raw/에 저장."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # URL에서 slug 생성
    url = url_info["url"]
    slug = url.split("//")[-1].split("?")[0].split("#")[0]
    slug = slug.replace("/", "-").replace(".", "-").strip("-")[:80]

    output_path = RAW_DIR / f"capture-{date_str}-{slug}.md"

    content = f"""---
type: playwright-capture
date: {date_str}
url: {url}
title: {url_info.get('title', '')}
source: {url_info.get('source', '')}
method: accessibility-tree
captured: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---

# {url_info.get('title', url)}

URL: {url}

## Accessibility Tree

{a11y_text}
"""
    output_path.write_text(content, encoding="utf-8")
    print(f"[playwright] saved: {output_path.name} ({len(a11y_text)} chars)")
    return output_path


def update_log(date_str, count):
    """vault/log.md에 캡처 내역 추가."""
    log_line = f"- [{date_str}] playwright-capture: {count} pages captured (a11y tree)\n"
    if LOG_FILE.exists():
        content = LOG_FILE.read_text(encoding="utf-8")
        if f"playwright-capture" not in content or date_str not in content:
            with LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(log_line)
    else:
        LOG_FILE.write_text(f"# Vault Log\n\n{log_line}", encoding="utf-8")


def main():
    # 인자 파싱
    if "--url" in sys.argv:
        idx = sys.argv.index("--url")
        if idx + 1 < len(sys.argv):
            url = sys.argv[idx + 1]
            date_str = datetime.now().strftime("%Y-%m-%d")
            urls = [{"url": url, "title": "", "source": "manual"}]
        else:
            print("Usage: playwright-capture.py --url <URL>")
            return
    else:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            date_str = sys.argv[1]
        else:
            date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        urls = get_high_value_urls(date_str)

    if not urls:
        print(f"[playwright] no URLs to capture for {date_str}")
        return

    print(f"[playwright] capturing {len(urls)} pages for {date_str}")

    captured = 0
    for url_info in urls:
        url = url_info["url"]
        print(f"[playwright] → {url[:80]}...")

        # accessibility tree 캡처
        raw_json = capture_with_script(url)
        if not raw_json:
            print(f"[playwright]   skip (no content)")
            continue

        # ariaSnapshot()은 이미 텍스트 형태
        a11y_text = raw_json

        if not a11y_text or len(a11y_text) < 50:
            print(f"[playwright]   skip (too short: {len(a11y_text)} chars)")
            continue

        save_capture(date_str, url_info, a11y_text)
        captured += 1

    if captured:
        update_log(date_str, captured)

    print(f"[playwright] done: {captured}/{len(urls)} pages captured")


if __name__ == "__main__":
    main()
