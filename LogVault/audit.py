from flask import session
from db import get_db_connection

def log_audit(action_type):
    """
    To store all actions being done in the audit table
    """
    user_id = session.get("user_id")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
         INSERT INTO audit_trail (user_id, action_type, action_time)
         VALUES (%s, %s, NOW())
         """, (user_id, action_type))

    conn.commit()
    cur.close()
    conn.close()
