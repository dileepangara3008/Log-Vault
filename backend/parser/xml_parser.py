import xml.etree.ElementTree as ET
from datetime import datetime

def parse_xml(path):
    logs = []

    tree = ET.parse(path)
    root = tree.getroot()

    # Expecting structure: <logs><log>...</log></logs>
    for log_elem in root.findall("log"):
        try:
            # --- timestamp ---
            ts_text = log_elem.findtext("timestamp")
            if not ts_text:
                continue

            # ISO format: 2026-01-12T09:00:01
            timestamp = datetime.fromisoformat(ts_text)

            # --- severity ---
            severity = log_elem.findtext("level", "INFO").upper()

            # --- service ---
            service = log_elem.findtext("service", "unknown")

            # --- message ---
            message = log_elem.findtext("message", "")

            # --- append extra fields ---
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
            # Skip malformed log entries safely
            continue

    return logs
