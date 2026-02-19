from functools import wraps
from flask import session, redirect, url_for, abort
from db import get_db_connection


def get_user_permissions(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT p.permission_key
        FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.permission_id
        WHERE ur.user_id = %s
    """, (user_id,))

    perms = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()
    return perms


def user_has_permission(user_id, permission_key):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.permission_id
        WHERE ur.user_id = %s AND p.permission_key = %s
        LIMIT 1
    """, (user_id, permission_key))

    ok = cur.fetchone() is not None

    cur.close()
    conn.close()
    return ok


def require_permission(permission_key):
    """
    Decorator for protecting Flask routes.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return redirect(url_for("auth.login"))

            if not user_has_permission(user_id, permission_key):
                abort(403, f"Permission denied: {permission_key}")

            return fn(*args, **kwargs)
        return wrapper
    return decorator
