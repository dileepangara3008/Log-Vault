"""
JSON Parser
"""
import json
import io
from parser.time_parser import parse_timestamp

def normalize_key(key):
    """
    Normalizing the keys
    """
    return "".join(c.lower() for c in key if c.isalnum())

TIMESTAMP_KEYS = {"timestamp", "time", "datetime", "logtime"}
SEVERITY_KEYS  = {"severity", "level", "loglevel"}
MESSAGE_KEYS   = {"message", "msg", "line", "content", "note"}

def get_normalized(entry, key_set, default=None):
    """
    Normalization
    """
    for k, v in entry.items():
        if normalize_key(k) in key_set and v:
            return v
    return default

def parse_json(file_stream):
    """
    Paring JSON function
    """
    logs = []
    raw_count = 0
    skipped_count = 0

    text_stream = io.TextIOWrapper(
        file_stream, encoding="utf-8", errors="ignore"
    )

    try:
        data = json.load(text_stream)
    except Exception:
        return logs, raw_count, skipped_count

    if not isinstance(data, list):
        return logs, raw_count, skipped_count

    for entry in data:
        raw_count += 1

        if not isinstance(entry, dict):
            skipped_count += 1
            continue

        ts_raw = get_normalized(entry, TIMESTAMP_KEYS)
        if not ts_raw:
            skipped_count += 1
            continue

        timestamp = parse_timestamp(ts_raw)
        if not timestamp:
            skipped_count += 1
            continue

        severity = get_normalized(entry, SEVERITY_KEYS, "INFO").upper()
        message  = get_normalized(entry, MESSAGE_KEYS, "")

        if message is None:
            skipped_count += 1
            continue

        for k, v in entry.items():
            if normalize_key(k) not in (TIMESTAMP_KEYS | SEVERITY_KEYS | MESSAGE_KEYS) and v is not None:
                message += f" | {k}={v}"

        logs.append({
            "timestamp": timestamp,
            "severity": severity,
            "message": message
        })

    return logs, raw_count, skipped_count

