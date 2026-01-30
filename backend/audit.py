from db import get_db_connection
from flask import session

def log_audit(action_type, entity_type=None, entity_id=None, details=None):
    user_id = session.get("user_id")

    conn = get_db_connection()
    cur = conn.cursor()

    # If your audit_trail has only 3 columns, use the simple insert:
    cur.execute("""
         INSERT INTO audit_trail (user_id, action_type, action_time)
         VALUES (%s, %s, NOW())
         """, (user_id, action_type))

    # If you upgraded audit_trail with entity_type/entity_id/details:
    # cur.execute("""
    #     INSERT INTO audit_trail (user_id, action_type, entity_type, entity_id, details, action_time)
    #     VALUES (%s, %s, %s, %s, %s, NOW())
    # """, (user_id, action_type, entity_type, entity_id, details))

    conn.commit()
    cur.close()
    conn.close()
