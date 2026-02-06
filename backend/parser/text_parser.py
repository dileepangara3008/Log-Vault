import re
from datetime import datetime

# -------- FORMAT 1: space-separated (service-based) --------
SPACE_FORMAT_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:,\d{3})?)\s+"
    r"(?P<severity>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s+"
    r"(?:\[(?P<thread>[^\]]+)\]\s+)?"
    r"(?P<service>[A-Za-z0-9_.-]+)\s*"
    r"(?:-\s+)?"
    r"(?P<message>.*)$"
)

# -------- FORMAT 2: pipe-separated --------
PIPE_FORMAT_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2},\d{3})\s*\|\s*"
    r"(?P<severity>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s*\|\s*"
    r"(?P<message>.+)$"
)

def parse_text(file_stream):
    logs = []
    current_log = None

    for raw_line in file_stream:
        line = raw_line.decode("utf-8", errors="ignore").rstrip()

        if not line:
            continue

        # Ignore separator lines (-----)
        if set(line.strip()) == {"-"}:
            continue

        match = SPACE_FORMAT_PATTERN.match(line)
        log_format = "SPACE"

        if not match:
            match = PIPE_FORMAT_PATTERN.match(line)
            log_format = "PIPE"

        if match:
            # save previous multiline log
            if current_log:
                logs.append(current_log)

            ts_raw = f"{match.group('date')} {match.group('time')}"
            ts_format = (
                "%Y-%m-%d %H:%M:%S,%f"
                if "," in match.group("time")
                else "%Y-%m-%d %H:%M:%S"
            )
            timestamp = datetime.strptime(ts_raw, ts_format)

            current_log = {
                "timestamp": timestamp,
                "severity": match.group("severity"),
                "service": (
                    match.groupdict().get("service")
                    if log_format == "SPACE"
                    else "unknown-service"
                ),
                "message": match.group("message")
            }
        else:
            # multiline continuation (stack traces, etc.)
            if current_log:
                current_log["message"] += "\n" + line

    if current_log:
        logs.append(current_log)

    return logs
