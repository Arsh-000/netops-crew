import json
import datetime
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.jsonl")


def log_event(agent_name: str, event: str, details: dict):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "agent": agent_name,
        "event": event,
        "details": details,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
