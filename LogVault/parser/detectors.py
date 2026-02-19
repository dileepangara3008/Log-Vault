def detect_category(message: str) -> str:
    """
    Detect log category based on message content.
    Priority matters: SECURITY > AUDIT > INFRASTRUCTURE > APPLICATION > UNCATEGORIZED
    """

    if not message:
        return "UNCATEGORIZED"

    msg = message.lower()

    # -------------------------
    # SECURITY (highest priority)
    # -------------------------
    security_keywords = [
        "login", "logged in", "logout",
        "authentication", "authorization",
        "access denied", "invalid credentials",
        "unauthorized", "forbidden", "token", "jwt", "password"
    ]

    if any(k in msg for k in security_keywords):
        return "SECURITY"

    # -------------------------
    # AUDIT
    # -------------------------
    audit_keywords = [
        "user", "uploaded", "deleted",
        "updated", "downloaded",
        "created", "modified", "accessed"
    ]

    if any(k in msg for k in audit_keywords):
        return "AUDIT"

    # -------------------------
    # INFRASTRUCTURE
    # -------------------------
    infra_keywords = [
        "database", "timeout",
        "memory", "cpu", "disk",
        "service unavailable", "server",
        "connection failed", "network",
        "node", "container", "pod"
    ]

    if any(k in msg for k in infra_keywords):
        return "INFRASTRUCTURE"

    # -------------------------
    # APPLICATION
    # -------------------------
    app_keywords = [
        "file processing", "validation",
        "successful", "completed", "failed",
        "error", "exception",
        "request", "response",
        "api", "service", "controller",
        "payment", "order"
    ]

    if any(k in msg for k in app_keywords):
        return "APPLICATION"

    # -------------------------
    # FALLBACK
    # -------------------------
    return "UNCATEGORIZED"
