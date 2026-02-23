from datetime import datetime, timezone

def parse_timestamp(value):
    """
    Unified timestamp parser for all log formats.

    Supported formats:
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

            if ts > 10**12:
                return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

            return datetime.fromtimestamp(ts, tz=timezone.utc)

        except (ValueError, OSError, OverflowError):
            return None

    # ---- Known fixed formats ----
    formats = (
        "%Y-%m-%d %H:%M:%S,%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # ---- ISO 8601 fallback ----
    try:
        iso_value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_value)

        # ensure UTC if timezone provided
        if dt.tzinfo:
            return dt.astimezone(timezone.utc)

        return dt.replace(tzinfo=timezone.utc)

    except ValueError:
        return None
