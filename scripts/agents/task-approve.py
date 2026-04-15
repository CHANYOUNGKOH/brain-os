#!/usr/bin/env python3
"""리뷰 완료된 태스크를 completed로 승인한다.
Usage: task-approve.py <queue-path> <task-id> [result-note]
"""
import json
import sys
from datetime import datetime

if len(sys.argv) < 3:
    print("Usage: task-approve.py <queue-path> <task-id> [result-note]")
    sys.exit(1)

queue_path = sys.argv[1]
task_id = sys.argv[2]
result_note = sys.argv[3] if len(sys.argv) > 3 else ""

with open(queue_path) as f:
    d = json.load(f)

found = False
for t in d["tasks"]:
    if t["id"] == task_id:
        if t.get("status") != "review":
            print(f"Warning: {task_id} is '{t.get('status')}' (not review)")
        t["status"] = "completed"
        t["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        if result_note:
            t["result"] = result_note
        found = True
        break

if not found:
    print(f"Error: {task_id} not found")
    sys.exit(1)

with open(queue_path, "w") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"{task_id} → completed")
