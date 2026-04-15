#!/usr/bin/env python3
"""task-queue에서 다음 디스패치할 태스크를 찾는다."""
import json
import sys

queue_path = sys.argv[1]

with open(queue_path) as f:
    d = json.load(f)

pending = []
blocked = []
for t in d.get("tasks", []):
    if t.get("status") != "pending":
        continue
    if t.get("agent") == "manual":
        continue
    dc = t.get("dispatch_count", 0)
    if dc >= 3:
        blocked.append(f"{t['id']}:{t.get('task', '')[:50]}")
        continue
    dep = t.get("depends_on")
    if dep:
        dep_done = any(
            x["id"] == dep and x["status"] == "completed" for x in d["tasks"]
        )
        if not dep_done:
            continue
    pending.append(f"{t['id']}|{t.get('agent', '')}|{t.get('task', '')[:80]}|{dc}")
    break

if pending:
    print(f"DISPATCH:{pending[0]}")
elif blocked:
    print(f"BLOCKED:{len(blocked)}:" + ",".join(blocked))
else:
    print("IDLE")
