"""
Parser Runner Module
"""
from io import BytesIO
import json
import csv
from io import StringIO
import xml.etree.ElementTree as ET
from db import get_db_connection
from .detectors import detect_category
from .text_parser import parse_text
from .csv_parser import parse_csv
from .json_parser import parse_json
from .xml_parser import parse_xml


PARSERS = {
    "TXT": parse_text,
    "CSV": parse_csv,
    "JSON": parse_json,
    "XML": parse_xml
}

def detect_format_from_content(raw_bytes):
    """
    Detect actual file format from content.
    Returns one of: JSON, XML, CSV, TXT
    """
    stripped = raw_bytes.lstrip()

    # ---- Try JSON ----
    try:
        json.loads(stripped.decode("utf-8"))
        return "JSON"
    except (ValueError, UnicodeDecodeError):
        pass

    # ---- Try XML ----
    try:
        ET.fromstring(stripped)
        return "XML"
    except ET.ParseError:
        pass

    # ---- Try CSV ----
    try:
        text = stripped.decode("utf-8")
        sample_lines = text.splitlines()[:5]
        sample_text = "\n".join(sample_lines)

        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample_text)

        reader = csv.reader(StringIO(sample_text), dialect)
        rows = list(reader)

        if rows and any(len(row) > 1 for row in rows):
            return "CSV"

    except (csv.Error, UnicodeDecodeError):
        pass

    # ---- Default ----
    return "TXT"


def run_parser(file_id, file_stream, format_name):
    """
    Reads the file stream and routes it to the appropriate parser
    based on file format.

    """
    raw_bytes = file_stream.read()
    if not raw_bytes:
        raise ValueError("Parser received empty file stream")

    # Detect actual format from file content
    detected_format = detect_format_from_content(raw_bytes)

    # Optional: log mismatch for audit/debug
    if format_name.upper() != detected_format:
        print(f"Extension says {format_name}, but detected {detected_format}")

    parser = PARSERS.get(detected_format)

    if not parser:
        raise ValueError(f"No parser available for detected format {detected_format}")


    parsed_logs, raw_total, skipped_by_parser = parser(BytesIO(raw_bytes))

    total_logs = raw_total
    skipped_logs = skipped_by_parser
    inserted_logs = 0

    if total_logs == 0:
        return total_logs, inserted_logs, skipped_logs

    conn = get_db_connection()
    cur = conn.cursor()

    # PRELOAD SEVERITIES
    cur.execute("SELECT severity_code, severity_id FROM log_severities")
    severity_map = dict(cur.fetchall())
    severity_map = {k.upper(): v for k, v in severity_map.items()}
    default_severity_id = severity_map.get("INFO")

    # PRELOAD CATEGORIES
    cur.execute("SELECT category_name, category_id FROM log_categories")
    category_map = dict(cur.fetchall())
    default_category_id = category_map.get("UNCATEGORIZED")

    for log in parsed_logs:
        try:
            timestamp = log.get("timestamp")
            severity = log.get("severity")
            message = log.get("message")

            # Validation
            if not timestamp or not message or not message.strip():
                skipped_logs += 1
                continue

            severity = (severity or "INFO").upper()
            severity_id = severity_map.get(severity, default_severity_id)

            # Category detection
            try:
                category = detect_category(message)
            except (ValueError, TypeError):
                category = "UNCATEGORIZED"

            category_id = category_map.get(category, default_category_id)

            # Insert log
            cur.execute("""
                INSERT INTO log_entries
                (file_id, log_timestamp, severity_id, category_id, message_line)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                file_id,
                timestamp,
                severity_id,
                category_id,
                message
            ))

            if cur.rowcount > 0:
                inserted_logs += 1

        except (ValueError, TypeError, KeyError):
            skipped_logs += 1
            continue

    conn.commit()
    cur.close()
    conn.close()

    return total_logs, inserted_logs, skipped_logs
