"""Logging utilities"""

import json
from datetime import datetime, timezone


def log_result(job_url, status, reason="", steps_completed=0):
    """Log application result to JSONL file"""
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_url": job_url,
        "status": status,
        "steps_completed": steps_completed,
    }
    if reason:
        result["failure_reason"] = reason
    
    with open("log.jsonl", "a") as f:
        f.write(json.dumps(result) + "\n")
    
    print(f"[{status}] {job_url}")
    if reason:
        print(f"  Reason: {reason}")
