#!/usr/bin/env python3
"""
Brain OS Scheduler — 크로스 플랫폼 스케줄러
macOS: crontab 등록
Windows: Task Scheduler 등록 (schtasks)
Linux: crontab 등록

Usage: scheduler.py install   — 스케줄 등록
       scheduler.py uninstall — 스케줄 제거
       scheduler.py status    — 현재 상태
"""
import os
import sys
import platform
import subprocess
from pathlib import Path

BRAIN_DIR = os.environ.get("BRAIN_OS_DIR", str(Path.home() / ".brain-os"))
PYTHON = sys.executable
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

# 스케줄 정의: (이름, 스크립트, 주기)
SCHEDULES = [
    ("brain-os-audit", "scripts/hermes-audit.py", "30min"),
    ("brain-os-capture", "scripts/capture-history.py", "daily-23:00"),
    ("brain-os-playwright", "scripts/playwright-capture.py", "daily-23:15"),
    ("brain-os-usermodel", "scripts/user-model-update.py", "daily-23:30"),
    ("brain-os-memorize", "scripts/auto-memorize.py", "daily-23:45"),
    ("brain-os-evolve", "scripts/auto-evolve.py", "daily-00:00"),
    ("brain-os-index", "scripts/vault-index-update.py", "daily-03:00"),
    ("brain-os-hygiene", "scripts/vault-hygiene.py", "daily-04:00"),
]


def install_crontab():
    """macOS/Linux: crontab 등록."""
    marker = "# Brain OS"
    existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout

    if marker in existing:
        print("Brain OS cron jobs already registered")
        return

    cron_map = {
        "30min": "*/30 * * * *",
        "daily-23:00": "0 23 * * *",
        "daily-23:15": "15 23 * * *",
        "daily-23:30": "30 23 * * *",
        "daily-23:45": "45 23 * * *",
        "daily-00:00": "0 0 * * *",
        "daily-03:00": "0 3 * * *",
        "daily-04:00": "0 4 * * *",
    }

    lines = [existing.rstrip(), "", marker]
    for name, script, schedule in SCHEDULES:
        script_path = os.path.join(BRAIN_DIR, script)
        cron_expr = cron_map.get(schedule, "0 * * * *")
        log_path = os.path.join(BRAIN_DIR, "scripts", f"{name}.log")
        lines.append(f"{cron_expr} {PYTHON} {script_path} >> {log_path} 2>&1")

    new_crontab = "\n".join(lines) + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True)
    if proc.returncode == 0:
        print(f"Registered {len(SCHEDULES)} cron jobs")
    else:
        print("Failed to register cron jobs")


def install_windows_tasks():
    """Windows: Task Scheduler 등록."""
    schedule_map = {
        "30min": "/sc minute /mo 30",
        "daily-23:00": "/sc daily /st 23:00",
        "daily-23:15": "/sc daily /st 23:15",
        "daily-23:30": "/sc daily /st 23:30",
        "daily-23:45": "/sc daily /st 23:45",
        "daily-00:00": "/sc daily /st 00:00",
        "daily-03:00": "/sc daily /st 03:00",
        "daily-04:00": "/sc daily /st 04:00",
    }

    for name, script, schedule in SCHEDULES:
        script_path = os.path.join(BRAIN_DIR, script)
        sched_args = schedule_map.get(schedule, "/sc daily /st 00:00")
        cmd = f'schtasks /create /tn "{name}" /tr "{PYTHON} {script_path}" {sched_args} /f'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  Registered: {name}")
        else:
            print(f"  Failed: {name} — {result.stderr.strip()}")

    print(f"Registered {len(SCHEDULES)} scheduled tasks")


def uninstall_crontab():
    existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    lines = []
    skip = False
    for line in existing.split("\n"):
        if line.strip() == "# Brain OS":
            skip = True
            continue
        if skip and line.strip().startswith("#"):
            skip = False
        if not skip:
            lines.append(line)
    subprocess.run(["crontab", "-"], input="\n".join(lines), text=True)
    print("Brain OS cron jobs removed")


def uninstall_windows_tasks():
    for name, _, _ in SCHEDULES:
        subprocess.run(f'schtasks /delete /tn "{name}" /f', shell=True, capture_output=True)
    print("Brain OS scheduled tasks removed")


def status():
    print(f"Platform: {platform.system()}")
    print(f"Brain OS dir: {BRAIN_DIR}")
    print(f"Python: {PYTHON}")
    print()

    if IS_WINDOWS:
        for name, _, _ in SCHEDULES:
            r = subprocess.run(f'schtasks /query /tn "{name}"', shell=True, capture_output=True, text=True)
            status = "registered" if r.returncode == 0 else "not found"
            print(f"  {name}: {status}")
    else:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        for name, _, _ in SCHEDULES:
            status = "registered" if name in existing else "not found"
            print(f"  {name}: {status}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"

    if action == "install":
        if IS_WINDOWS:
            install_windows_tasks()
        else:
            install_crontab()
    elif action == "uninstall":
        if IS_WINDOWS:
            uninstall_windows_tasks()
        else:
            uninstall_crontab()
    elif action == "status":
        status()
    else:
        print(f"Usage: scheduler.py [install|uninstall|status]")
