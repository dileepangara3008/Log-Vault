from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from werkzeug.utils import secure_filename
from db import get_db_connection
from audit import log_audit
from permissions import require_permission
from parser.parser_runner import run_parser

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {
    "txt": "TXT",
    "csv": "CSV",
    "json": "JSON",
    "xml": "XML"
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/upload", methods=["GET", "POST"])
@require_permission("UPLOAD_LOG")
def upload_file():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # admin check
    cur.execute("""
        SELECT 1
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.role_id
        WHERE ur.user_id = %s AND r.role_name = 'ADMIN'
        LIMIT 1
    """, (user_id,))
    admin = cur.fetchone() is not None

    cur.execute("SELECT environment_id, environment_code FROM environments")
    environments = cur.fetchall()

    if request.method == "POST":
        file = request.files.get("file")
        environment_id = request.form.get("environment_id")

        if not environment_id:
            abort(400, "Environment is required")
        if not file or file.filename == "":
            abort(400, "No file selected")
        if not allowed_file(file.filename):
            abort(400, "Unsupported file type")

        filename = secure_filename(file.filename)
        extension = filename.rsplit(".", 1)[1].lower()
        format_name = ALLOWED_EXTENSIONS[extension]

        # format_id
        cur.execute(
            "SELECT format_id FROM file_formats WHERE format_name=%s",
            (format_name,)
        )
        format_id = cur.fetchone()[0]

        # team_id
        cur.execute(
            "SELECT team_id FROM user_teams WHERE user_id=%s LIMIT 1",
            (user_id,)
        )
        team_id = cur.fetchone()[0]

        # file size (memory-safe)
        file_bytes = file.read()
        file_size = len(file_bytes)
        file.seek(0)

        # insert raw_files
        cur.execute("""
            INSERT INTO raw_files
            (team_id, uploaded_by, original_name, file_size_bytes, format_id, environment_id)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING file_id
        """, (
            team_id,
            user_id,
            filename,
            file_size,
            format_id,
            environment_id
        ))

        file_id = cur.fetchone()[0]
        log_audit("UPLOAD_FILE", "raw_files", file_id, f"Uploaded {filename}")
        conn.commit()

        try:
            run_parser(file_id, file.stream)
            success = "1"
            error = None
        except Exception as e:
            conn.rollback()
            success = None
            error = "Parsing failed. Please check the log format."

        cur.close()
        conn.close()

        if success:
            return redirect(url_for("upload.upload_file", success="1"))
        else:
            return redirect(url_for("upload.upload_file", error="1"))


    cur.close()
    conn.close()
    return render_template("upload.html", environments=environments, admin=admin)
