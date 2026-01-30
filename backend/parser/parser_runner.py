import sys
import os

# Add backend directory to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from db import get_db_connection
from detectors import detect_category
from text_parser import parse_text
from csv_parser import parse_csv
from json_parser import parse_json
from xml_parser import parse_xml


file_id_arg = None
if len(sys.argv) > 1:
    file_id_arg = int(sys.argv[1])


PARSERS = {
    "TXT": parse_text,
    "CSV": parse_csv,
    "JSON": parse_json,
    "XML": parse_xml
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")


def run_parser():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
            SELECT rf.file_id, rf.original_name, ff.format_name
            FROM raw_files rf
            JOIN file_formats ff ON rf.format_id = ff.format_id
            WHERE rf.file_id = %s AND rf.is_archived=FALSE
            """, (file_id_arg,))
    files = cur.fetchall()
    print("Files to parse:", files)
    for file_id, filename, format_name in files:
        try:
            path = os.path.join(UPLOAD_DIR, filename)
            print("Parsing:", path)
            parser = PARSERS.get(format_name)
            if not parser:
                raise Exception(f"No parser for format {format_name}")
            parsed_logs = parser(path)
            print("Parsed log count:", len(parsed_logs))
            for log in parsed_logs:
                severity = log["severity"].upper()

                #getting severity_id
                cur.execute(
                    "SELECT severity_id FROM log_severities WHERE severity_code=%s",
                    (severity,)
                )
                severity_row = cur.fetchone()
                if not severity_row:
                    continue
                severity_id = severity_row[0]

                #detecting category
                category = detect_category(log["message"])
                #getting category_id
                cur.execute(
                    "SELECT category_id FROM log_categories WHERE category_name=%s",
                    (category,)
                )
                category_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO log_entries
                    (file_id, log_timestamp, severity_id, category_id, message_line)
                    VALUES (%s,%s,%s,%s,%s)
                """, (
                    file_id,
                    log["timestamp"],
                    severity_id,
                    category_id,
                    log["message"]
                ))

            conn.commit()

        except Exception as e:
            print(f"FAILED parsing file {file_id}:", e)
            conn.rollback()

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_parser()
