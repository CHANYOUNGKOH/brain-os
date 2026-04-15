#!/usr/bin/env python3
"""태스크를 review 상태로 변경하고 결과를 저장한다."""
import json
import sys

queue_path = sys.argv[1]
task_id = sys.argv[2]
result_summary = sys.argv[3] if len(sys.argv) > 3 else ""
exit_code = int(sys.argv[4]) if len(sys.argv) > 4 else 0
elapsed = sys.argv[5] if len(sys.argv) > 5 else "0"

with open(queue_path) as f:
    d = json.load(f)

for t in d["tasks"]:
    if t["id"] == task_id:
        t["status"] = "review"
        if exit_code == 0:
            t["review_note"] = f"Completed ({elapsed}s). Review needed."
        else:
            t["review_note"] = f"Failed (exit={exit_code}, {elapsed}s). Review needed."
        if result_summary:
            t["result_preview"] = result_summary[:500]
        break

with open(queue_path, "w") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"{task_id} → review")
