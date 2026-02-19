"""
XML log parser.

Parses XML files structured as:
<logs>
    <log>
        ...
    </log>
</logs>

Extracts timestamp, severity, and message fields.
Appends extra fields into the message for context.
"""

from datetime import datetime
import xml.etree.ElementTree as ET


TIMESTAMP_KEYS = {"timestamp", "time", "datetime", "logtime"}
SEVERITY_KEYS = {"severity", "level", "loglevel"}
MESSAGE_KEYS = {"message", "msg", "line", "content", "note"}

ALL_CORE_KEYS = TIMESTAMP_KEYS | SEVERITY_KEYS | MESSAGE_KEYS


def parse_timestamp(value):
    """
    Parses ISO formatted timestamp.
    Returns None if invalid.
    """
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def normalize_key(key):
    """
    Normalizes XML tag names to lowercase alphanumeric.
    """
    return "".join(c.lower() for c in key if c.isalnum())


def parse_xml(file_stream):
    """
    Parses XML log file stream.

    Returns:
        tuple:
            logs (list),
            raw_count (int),
            skipped_count (int)
    """
    logs = []
    raw_count = 0
    skipped_count = 0

    try:
        raw = file_stream.read()
    except (OSError, AttributeError):
        return logs, raw_count, skipped_count

    if not raw:
        return logs, raw_count, skipped_count

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return logs, raw_count, skipped_count

    for log_elem in root.findall(".//log"):
        raw_count += 1

        try:
            timestamp = None
            severity = "INFO"
            message = ""

            # ---- First pass: extract core fields ----
            for child in log_elem:
                key = normalize_key(child.tag)
                value = (child.text or "").strip()

                if not value:
                    continue

                if key in TIMESTAMP_KEYS and not timestamp:
                    timestamp = parse_timestamp(value)

                elif key in SEVERITY_KEYS:
                    severity = value.upper()

                elif key in MESSAGE_KEYS and not message:
                    message = value

            if not timestamp:
                skipped_count += 1
                continue

            # ---- Second pass: append extra fields ----
            for child in log_elem:
                key = normalize_key(child.tag)
                value = (child.text or "").strip()

                if not value:
                    continue

                if key not in ALL_CORE_KEYS:
                    message += f" | {child.tag}={value}"

            logs.append({
                "timestamp": timestamp,
                "severity": severity,
                "message": message
            })

        except (ValueError, TypeError):
            skipped_count += 1
            continue

    return logs, raw_count, skipped_count
