from db import get_db_connection
from flask import session

def log_audit(action_type, entity_type=None, entity_id=None, details=None):
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
