import re
from datetime import datetime

GLOBAL_TXT_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:,\d{3})?)\s+"
    r"(?P<severity>DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\s+"
    r"(?:\[(?P<thread>[^\]]+)\]\s+)?"          # optional [thread]
    r"(?P<service>[A-Za-z0-9_.-]+)\s*"         # service name
    r"(?:-\s+)?"                               # optional " - "
    r"(?P<message>.*)$"
)

def parse_text(path):
    logs = []
    current_log = None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip()

            if not line.strip():
                continue

            m = GLOBAL_TXT_PATTERN.match(line)

            if m:
                # save previous log
                if current_log:
                    logs.append(current_log)

                ts_raw = f"{m.group('date')} {m.group('time')}"
                fmt = "%Y-%m-%d %H:%M:%S,%f" if "," in m.group("time") else "%Y-%m-%d %H:%M:%S"
                timestamp = datetime.strptime(ts_raw, fmt)

                current_log = {
                    "timestamp": timestamp,
                    "severity": m.group("severity"),
                    "service": m.group("service"),
                    "message": m.group("message"),
                    "raw": line
                }
            else:
                # continuation / stacktrace line
                if current_log:
                    current_log["message"] += "\n" + line

    if current_log:
        logs.append(current_log)

    return logs
