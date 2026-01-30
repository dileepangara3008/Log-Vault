import json
from datetime import datetime

def parse_json(path):
    logs = []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

        # Expecting a list of log objects
        if not isinstance(data, list):
            return logs

        for entry in data:
            try:
                timestamp_str = entry.get("timestamp")
                if not timestamp_str:
                    continue

                timestamp = datetime.fromisoformat(timestamp_str)
                severity = entry.get("level", "INFO").upper()
                service = entry.get("service", "unknown")
                message = entry.get("message", "")
                extra_fields = []
                for key, value in entry.items():
                    if key not in ("timestamp", "level", "service", "message", "thread"):
                        extra_fields.append(f"{key}={value}")

                if extra_fields:
                    message = message + " | " + " ".join(extra_fields)

                logs.append({
                    "timestamp": timestamp,
                    "severity": severity,
                    "service": service,
                    "message": message
                })

            except Exception:
                continue

    return logs
