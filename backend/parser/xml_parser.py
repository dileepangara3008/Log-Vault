import json
from datetime import datetime
import io

def parse_json(file_stream):
    logs = []

    # Read bytes first (safe)
    try:
        raw_bytes = file_stream.read()
    except Exception:
        return logs

    if not raw_bytes:
        return logs

    # Decode once
    try:
        text = raw_bytes.decode("utf-8", errors="ignore")
        data = json.loads(text)
    except Exception:
        return logs

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
