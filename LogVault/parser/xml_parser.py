"""
XML Log Parser

Parses XML files structured as:

<logs>
    <log>
        ...
    </log>
</logs>

Extracts:
- timestamp (mandatory)
- severity (optional, defaults to INFO)
- message (mandatory if timestamp valid)

Extra fields are appended to message.
"""

from datetime import datetime
import xml.etree.ElementTree as ET


TIMESTAMP_KEYS = {"timestamp", "time", "datetime", "logtime"}
SEVERITY_KEYS = {"severity", "level", "loglevel"}
MESSAGE_KEYS = {"message", "msg", "line", "content", "note"}


def parse_timestamp(value):
    """
    Parses ISO timestamp and supports trailing 'Z'.
    Returns None if invalid.
    """
    try:
        value = value.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(value)
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

    # ---- Read file ----
    try:
        raw = file_stream.read()
    except (OSError, AttributeError):
        return logs, raw_count, skipped_count

    if not raw:
        return logs, raw_count, skipped_count

    # ---- Parse XML ----
    try:
        root = ET.fromstring(raw.decode("utf-8", errors="ignore"))
    except ET.ParseError:
        return logs, raw_count, skipped_count

    # ---- Process each <log> element ----
    for log_elem in root.findall(".//log"):
        raw_count += 1

        timestamp = None
        severity = "INFO"
        message = ""

        # ---- First pass: core fields ----
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

        # ---- Validate timestamp ----
        if not timestamp:
            skipped_count += 1
            continue

        # ---- Second pass: append extra fields ----
        for child in log_elem:
            key = normalize_key(child.tag)
            value = (child.text or "").strip()

            if not value:
                continue

            if key not in (TIMESTAMP_KEYS | SEVERITY_KEYS | MESSAGE_KEYS):
                message += f" | {child.tag}={value}"

        logs.append({
            "timestamp": timestamp,
            "severity": severity,
            "message": message
        })

    return logs, raw_count, skipped_count
