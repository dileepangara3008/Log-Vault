"""
CSV Parser
"""
import csv
import io
from parser.time_parser import parse_timestamp

TIMESTAMP_COLS = ["timestamp", "time", "datetime"]
SEVERITY_COLS  = ["severity", "level"]
MESSAGE_COLS   = ["message", "line", "content", "note"]

def get_value(row, keys, default=None):
    """
    Getting value for key
    """
    for k in keys:
        if k in row and row[k]:
            return row[k]
    return default


def parse_csv(file_stream):
    """
    Parsing CSV file
    """
    logs = []
    raw_count = 0
    skipped_count = 0

    text = io.TextIOWrapper(file_stream, encoding="utf-8", errors="ignore")

    first_line = text.readline()
    text.seek(0)

    has_header = any(col in first_line.lower() for col in TIMESTAMP_COLS)

    # -------- CSV WITH HEADER --------
    if has_header:
        reader = csv.DictReader(text)
        reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]

        for row in reader:
            raw_count += 1

            ts_raw = get_value(row, TIMESTAMP_COLS)
            if not ts_raw:
                skipped_count += 1
                continue

            timestamp = parse_timestamp(ts_raw)
            if not timestamp:
                skipped_count += 1
                continue

            severity = get_value(row, SEVERITY_COLS, "INFO").upper()
            message  = get_value(row, MESSAGE_COLS, "")

            if message is None:
                skipped_count += 1
                continue

            for k, v in row.items():
                if k not in TIMESTAMP_COLS + SEVERITY_COLS + MESSAGE_COLS and v:
                    message += f" | {k}={v}"

            logs.append({
                "timestamp": timestamp,
                "severity": severity,
                "message": message
            })

    # -------- CSV WITHOUT HEADER --------
    else:
        reader = csv.reader(text)

        for row in reader:
            raw_count += 1

            if len(row) < 2:
                skipped_count += 1
                continue

            timestamp = parse_timestamp(row[0])
            if not timestamp:
                skipped_count += 1
                continue

            severity = row[1].strip().upper() if row[1] else "INFO"
            message  = " | ".join(col.strip() for col in row[2:] if col)

            logs.append({
                "timestamp": timestamp,
                "severity": severity,
                "message": message
            })

    return logs, raw_count, skipped_count
