import json
from datetime import datetime
import io

def parse_json(file_stream):
    logs = []

    # Wrap bytes stream → text stream for json
    text_stream = io.TextIOWrapper(file_stream, encoding="utf-8", errors="ignore")

    try:
        data = json.load(text_stream)
    except Exception:
        return logs

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
                    if value is not None:
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
