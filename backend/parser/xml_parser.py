import xml.etree.ElementTree as ET
from datetime import datetime

def parse_xml(file_stream):
    logs = []

    try:
        raw_bytes = file_stream.read()
    except Exception:
        return logs

    if not raw_bytes:
        return logs

    try:
        root = ET.fromstring(raw_bytes)
    except Exception:
        return logs

    # Expecting structure: <logs><log>...</log></logs>
    for log_elem in root.findall("log"):
        try:
            ts_text = log_elem.findtext("timestamp")
            if not ts_text:
                continue

            timestamp = datetime.fromisoformat(ts_text)
            severity = log_elem.findtext("level", "INFO").upper()
            service = log_elem.findtext("service", "unknown")
            message = log_elem.findtext("message", "")

            extra_fields = []
            for child in log_elem:
                tag = child.tag
                text = (child.text or "").strip()

                if tag not in ("timestamp", "level", "service", "message", "thread") and text:
                    extra_fields.append(f"{tag}={text}")

            if extra_fields:
                message = message + " | " + " ".join(extra_fields)

            logs.append({
                "timestamp": timestamp,
                "severity": severity,
                "service": service,
                "message": message
            })

        except Exception:
            continue

    return logs
