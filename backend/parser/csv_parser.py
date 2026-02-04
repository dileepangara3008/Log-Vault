import csv
from datetime import datetime
import io

def parse_csv(file_stream):
    logs = []
    text_stream = io.TextIOWrapper(file_stream, encoding="utf-8", errors="ignore")
    reader = csv.DictReader(text_stream)

    if not reader.fieldnames:
        return logs

    reader.fieldnames = [h.lower() for h in reader.fieldnames]

    for row in reader:
        try:
            ts = row.get("timestamp")
            if not ts:
                continue

            try:
                timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f")
            except ValueError:
                timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

            severity = row.get("level", "INFO").upper()
            service = row.get("service", "unknown")
            message = row.get("message", "")

            extras = []
            for k, v in row.items():
                if k not in ("timestamp", "level", "service", "message", "thread"):
                    if v:
                        extras.append(f"{k}={v}")

            if extras:
                message += " | " + " ".join(extras)

            logs.append({
                "timestamp": timestamp,
                "severity": severity,
                "service": service,
                "message": message
            })

        except Exception as e:
            print("CSV error:", e)

    return logs

