#!/usr/bin/env python3
"""텔레그램 메시지 전송. brain-os.env에서 설정 읽기."""
import os
import sys
import urllib.request
import urllib.parse
import json
from pathlib import Path

BRAIN_DIR = os.environ.get("BRAIN_OS_DIR", str(Path.home() / ".brain-os"))
ENV_FILE = os.path.join(BRAIN_DIR, "brain-os.env")

# 환경변수에서 읽기 (brain-os.env 또는 시스템 환경변수)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# brain-os.env 파싱 (셸 source 대용)
if not BOT_TOKEN and os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            val = val.strip().strip('"').strip("'")
            if key.strip() == "TELEGRAM_BOT_TOKEN":
                BOT_TOKEN = val
            elif key.strip() == "TELEGRAM_CHAT_ID":
                CHAT_ID = val

# 토픽 매핑 (선택 — 그룹+토픽 사용 시)
TOPICS = {}
topic_prefix = "TELEGRAM_TOPIC_"
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith(topic_prefix):
                key, _, val = line.partition("=")
                topic_name = key[len(topic_prefix):].lower()
                TOPICS[topic_name] = int(val.strip().strip('"'))


def send(msg, topic="general"):
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set", file=sys.stderr)
        return False

    params = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
    }

    thread_id = TOPICS.get(topic)
    if thread_id:
        params["message_thread_id"] = thread_id

    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)
        return False


def send_file(file_path, topic="general"):
    """파일 전송."""
    if not BOT_TOKEN or not CHAT_ID:
        return False

    boundary = "----BrainOSBoundary"
    with open(file_path, "rb") as f:
        file_data = f.read()

    filename = os.path.basename(file_path)
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{CHAT_ID}\r\n"
    )

    thread_id = TOPICS.get(topic)
    if thread_id:
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="message_thread_id"\r\n\r\n'
            f"{thread_id}\r\n"
        )

    body = body.encode() + (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"Telegram file error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: send-telegram.py <message> [topic]")
        print("       send-telegram.py --file <path> [topic]")
        sys.exit(1)

    if sys.argv[1] == "--file":
        path = sys.argv[2]
        topic = sys.argv[3] if len(sys.argv) > 3 else "general"
        ok = send_file(path, topic)
    else:
        msg = sys.argv[1]
        topic = sys.argv[2] if len(sys.argv) > 2 else "general"
        ok = send(msg, topic)

    sys.exit(0 if ok else 1)
