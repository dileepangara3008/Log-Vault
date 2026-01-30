import os
from flask import Blueprint, render_template, session, redirect, url_for, request, abort
from db import get_db_connection
from audit import log_audit
from config import UPLOAD_FOLDER

files_bp = Blueprint("files", __name__)

def is_admin_user(cur, user_id):
    cur.execute("""
        SELECT 1
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.role_id
        WHERE ur.user_id = %s AND LOWER(r.role_name) = 'admin'
        LIMIT 1
    """, (user_id,))
    return cur.fetchone() is not None



@files_bp.route("/files")
def list_files():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    admin = is_admin_user(cur, user_id)

    if admin:
        cur.execute("""
            SELECT rf.file_id, rf.original_name, rf.file_size_bytes, rf.uploaded_at,
                   u.email, t.team_name, rf.is_archived
            FROM raw_files rf
            JOIN users u ON rf.uploaded_by = u.user_id
            JOIN teams t ON rf.team_id = t.team_id
            ORDER BY rf.uploaded_at DESC
        """)
    else:
        cur.execute("""
            SELECT rf.file_id, rf.original_name, rf.file_size_bytes, rf.uploaded_at,
                   u.email, t.team_name, rf.is_archived
            FROM raw_files rf
            JOIN users u ON rf.uploaded_by = u.user_id
            JOIN teams t ON rf.team_id = t.team_id
            WHERE rf.uploaded_by = %s AND rf.is_archived=FALSE
            ORDER BY rf.uploaded_at DESC
        """, (user_id,))

    files = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("files.html", files=files, admin=admin)


@files_bp.route("/files/<int:file_id>/delete", methods=["POST"])
def delete_file(file_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    admin = is_admin_user(cur, user_id)

    # Fetch file info
    cur.execute("""
        SELECT file_id, original_name, uploaded_by
        FROM raw_files
        WHERE file_id = %s
    """, (file_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        abort(404, "File not found")

    file_id_db, filename, uploaded_by = row

    # Permission check
    if not admin and uploaded_by != user_id:
        cur.close()
        conn.close()
        abort(403, "You can delete only your uploaded files")

    # Delete file from disk
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from DB (log_entries will be deleted automatically because ON DELETE CASCADE)
    cur.execute("DELETE FROM raw_files WHERE file_id=%s", (file_id,))
    conn.commit()

    log_audit("DELETE_FILE", "raw_files", file_id, f"Deleted file {filename}")

    cur.close()
    conn.close()

    return redirect(url_for("files.list_files"))

@files_bp.route("/files/<int:file_id>/archive", methods=["POST"])
def archive_file(file_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    admin = is_admin_user(cur, user_id)
    if not admin:
        cur.close()
        conn.close()
        abort(403, "Only admin can archive files")

    # Fetch file info
    cur.execute("""
        SELECT file_id, original_name, is_archived
        FROM raw_files
        WHERE file_id = %s
    """, (file_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        abort(404, "File not found")

    file_id_db, filename, is_archived = row

    # If already archived, do nothing
    if is_archived:
        cur.close()
        conn.close()
        return redirect(url_for("files.list_files"))

    # Count total logs for that file
    cur.execute("""
        SELECT COUNT(*)
        FROM log_entries
        WHERE file_id = %s
    """, (file_id,))
    total_records = cur.fetchone()[0]

    # Insert into archives table
    cur.execute("""
        INSERT INTO archives (file_id, archived_on, total_records)
        VALUES (%s, NOW(), %s)
    """, (file_id, total_records))

    # Mark raw_files as archived
    cur.execute("""
        UPDATE raw_files
        SET is_archived = TRUE
        WHERE file_id = %s
    """, (file_id,))

    conn.commit()

    log_audit("ARCHIVE_FILE", "raw_files", file_id, f"Archived file {filename}")

    cur.close()
    conn.close()

    return redirect(url_for("files.list_files"))


@files_bp.route("/files/<int:file_id>/restore", methods=["POST"])
def restore_file(file_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    admin = is_admin_user(cur, user_id)
    if not admin:
        cur.close()
        conn.close()
        abort(403, "Only admin can restore archived files")

    # Check file exists
    cur.execute("""
        SELECT file_id, original_name
        FROM raw_files
        WHERE file_id = %s
    """, (file_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        abort(404, "File not found")

    filename = row[1]

    cur.execute("DELETE FROM archives WHERE file_id = %s", (file_id,))

    # Restore file (unarchive)
    cur.execute("""
        UPDATE raw_files
        SET is_archived = FALSE
        WHERE file_id = %s
    """, (file_id,))

    conn.commit()

    log_audit("RESTORE_FILE", "raw_files", file_id, f"Restored file {filename}")

    cur.close()
    conn.close()

    return redirect(url_for("files.list_files"))
