"""
Parsing TXT file.

Supports:
- Space-separated log format
- Pipe-separated log format
- Multiline log messages
"""

import re
from parser.time_parser import parse_timestamp


SPACE_PATTERN = re.compile(
    r"^\[?(?P<date>\d{4}-\d{2}-\d{2})[T\s]+"
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:[.,]\d{3})?)(?:Z)?\]?\s+"
    r"(?P<severity>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s+"
    r"(?:\[[^\]]+\]\s+)?"
    r"(?:[A-Za-z0-9_.-]+\s*-\s*)?"
    r"(?P<message>.*)$",
    re.IGNORECASE
)

PIPE_PATTERN = re.compile(
    r"^\[?(?P<date>\d{4}-\d{2}-\d{2})[T\s]+"
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:[.,]\d{3})?)(?:Z)?\]?\s*\|\s*"
    r"(?P<severity>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s*\|\s*"
    r"(?P<message>.+)$",
    re.IGNORECASE
)


def parse_text(file_stream):
    """
    Parses a TXT log file stream.

    Returns:
        tuple:
            logs (list),
            raw_count (int),
            skipped_count (int)
    """
    logs = []
    current_log = None
    raw_count = 0
    skipped_count = 0

    for raw_line in file_stream:
        line = raw_line.decode("utf-8", errors="ignore").rstrip()

        if not line:
            continue

        if set(line.strip()) == {"-"}:
            continue

        match = SPACE_PATTERN.match(line) or PIPE_PATTERN.match(line)

        if match:
            raw_count += 1

            # Save previous log before starting a new one
            if current_log:
                logs.append(current_log)

            timestamp = parse_timestamp(
                f"{match.group('date')} {match.group('time')}"
            )

            if not timestamp:
                skipped_count += 1
                current_log = None
                continue

            current_log = {
                "timestamp": timestamp,
                "severity": match.group("severity").upper(),
                "message": match.group("message"),
            }

        else:
            # Multiline continuation
            if current_log:
                current_log["message"] += "\n" + line

    if current_log:
        logs.append(current_log)

    skipped_count += raw_count - len(logs)

    return logs, raw_count, skipped_count
