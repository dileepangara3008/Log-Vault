import os
from flask import Blueprint, render_template, session, redirect, url_for, abort
from db import get_db_connection
from queries import (
    GET_ALL_FILES_ADMIN,
    GET_USER_FILES,
    GET_FILE_BY_ID,
    DELETE_FILE,
    COUNT_FILE_LOGS,
    INSERT_ARCHIVE,
    MARK_FILE_ARCHIVED,
    UNARCHIVE_FILE,
    DELETE_ARCHIVE
)
from audit import log_audit
from config import UPLOAD_FOLDER

files_bp = Blueprint("files", __name__)


# =====================================================
# LIST FILES
# =====================================================

@files_bp.route("/files")
def list_files():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    is_admin = session.get("is_admin", False)

    conn = get_db_connection()
    cur = conn.cursor()

    if is_admin:
        cur.execute(GET_ALL_FILES_ADMIN)
    else:
        cur.execute(GET_USER_FILES, (user_id,))

    files = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("files.html", files=files, admin=is_admin)


# =====================================================
# DELETE FILE
# =====================================================

@files_bp.route("/files/<int:file_id>/delete", methods=["POST"])
def delete_file(file_id):

    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    is_admin = session.get("is_admin", False)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(GET_FILE_BY_ID, (file_id,))
    row = cur.fetchone()

    if not row:
        abort(404, "File not found")

    file_id_db, filename, uploaded_by, _ = row

    if not is_admin and uploaded_by != user_id:
        abort(403, "You can delete only your uploaded files")

    # Delete file from disk
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    cur.execute(DELETE_FILE, (file_id,))
    conn.commit()

    log_audit(f"Deleted file {filename}")

    cur.close()
    conn.close()

    return redirect(url_for("files.list_files"))


# =====================================================
# ARCHIVE FILE
# =====================================================

@files_bp.route("/files/<int:file_id>/archive", methods=["POST"])
def archive_file(file_id):

    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    if not session.get("is_admin", False):
        abort(403, "Only admin can archive files")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(GET_FILE_BY_ID, (file_id,))
    row = cur.fetchone()

    if not row:
        abort(404, "File not found")

    file_id_db, filename, _, is_archived = row

    if is_archived:
        return redirect(url_for("files.list_files"))

    cur.execute(COUNT_FILE_LOGS, (file_id,))
    total_records = cur.fetchone()[0]

    cur.execute(INSERT_ARCHIVE, (file_id, total_records))
    cur.execute(MARK_FILE_ARCHIVED, (file_id,))

    conn.commit()

    log_audit(f"Archived file {filename}")

    cur.close()
    conn.close()

    return redirect(url_for("files.list_files"))


# =====================================================
# RESTORE FILE
# =====================================================

@files_bp.route("/files/<int:file_id>/restore", methods=["POST"])
def restore_file(file_id):

    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    if not session.get("is_admin", False):
        abort(403, "Only admin can restore archived files")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(GET_FILE_BY_ID, (file_id,))
    row = cur.fetchone()

    if not row:
        abort(404, "File not found")

    filename = row[1]

    cur.execute(DELETE_ARCHIVE, (file_id,))
    cur.execute(UNARCHIVE_FILE, (file_id,))

    conn.commit()

    log_audit(f"Restored file {filename}")

    cur.close()
    conn.close()

    return redirect(url_for("files.list_files"))
