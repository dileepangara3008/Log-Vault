from io import BytesIO
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

def run_parser(file_id, file_stream):
    conn = get_db_connection()
    cur = conn.cursor()

    # 🔥 Read file ONCE
    raw_bytes = file_stream.read()
    if not raw_bytes:
        return

    cur.execute("""
        SELECT ff.format_name
        FROM raw_files rf
        JOIN file_formats ff ON rf.format_id = ff.format_id
        WHERE rf.file_id=%s AND rf.is_archived=FALSE
    """, (file_id,))

    row = cur.fetchone()
    if not row:
        return

    format_name = row[0]
    parser = PARSERS.get(format_name)
    if not parser:
        raise Exception(f"No parser for format {format_name}")

    # 🔥 Pass fresh stream
    parsed_logs = parser(BytesIO(raw_bytes))

    for log in parsed_logs:
        severity = log["severity"].upper()

        cur.execute(
            "SELECT severity_id FROM log_severities WHERE severity_code=%s",
            (severity,)
        )
        severity_row = cur.fetchone()
        if not severity_row:
            cur.execute(
                "SELECT severity_id FROM log_severities WHERE severity_code='INFO'"
            )
            severity_id = cur.fetchone()[0]
        else:
            severity_id = severity_row[0]

        category = detect_category(log["message"])

        cur.execute(
            "SELECT category_id FROM log_categories WHERE category_name=%s",
            (category,)
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                "SELECT category_id FROM log_categories WHERE category_name='GENERAL'"
            )
            category_id = cur.fetchone()[0]
        else:
            category_id = row[0]

        cur.execute("""
            INSERT INTO log_entries
            (file_id, log_timestamp, severity_id, category_id, message_line)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            file_id,
            log.get("timestamp"),
            severity_id,
            category_id,
            log.get("message")
        ))

    conn.commit()
    cur.close()
    conn.close()
