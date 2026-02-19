from datetime import datetime, timezone


def parse_timestamp(value):
    """
    Unified timestamp parser for all log formats.

    Supported:
    - YYYY-MM-DD HH:MM:SS
    - YYYY-MM-DD HH:MM:SS,mmm
    - ISO-8601 (with or without timezone)
    - Epoch seconds
    - Epoch milliseconds
    """

    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    # ---- Epoch timestamps ----
    if value.isdigit():
        try:
            ts = int(value)
            # milliseconds
            if ts > 10**12:
                return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            # seconds
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None

    # ---- Known fixed formats ----
    formats = [
        "%Y-%m-%d %H:%M:%S,%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass

    # ---- ISO 8601 fallback ----
    try:
        # handle trailing Z
        value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return None
