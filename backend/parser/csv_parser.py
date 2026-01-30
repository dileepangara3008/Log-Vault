import csv
from datetime import datetime
import io

def parse_csv(file_stream):
    logs = []

    # csv module expects text stream → wrap bytes stream
    text_stream = io.TextIOWrapper(file_stream, encoding="utf-8", errors="ignore")

    reader = csv.DictReader(text_stream)

    for row in reader:
        try:
            ts = row.get("timestamp")
            if not ts:
                continue

            timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            severity = row.get("level", "INFO").upper()
            service = row.get("service", "unknown")
            message = row.get("message", "")

            extra_fields = []
            for key, value in row.items():
                if key in ("timestamp", "level", "service", "message", "thread"):
                    continue
                if value and value.strip():
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
