from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from werkzeug.utils import secure_filename
from db import get_db_connection
from audit import log_audit
from permissions import require_permission
from parser.parser_runner import run_parser
import hashlib
from io import BytesIO

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {
    "txt": "TXT",
    "csv": "CSV",
    "json": "JSON",
    "xml": "XML"
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ... existing imports remain the same

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
        parsed_files = []
        duplicate_files = []
        failed_files = []

        overall_total = 0
        overall_inserted = 0

        files = request.files.getlist("files")
        environment_id = request.form.get("environment_id")

        if not environment_id:
            abort(400, "Environment is required")

        for file in files:
            if not file or file.filename == "":
                continue

            if not allowed_file(file.filename):
                abort(400, "Unsupported file type")

            filename = secure_filename(file.filename)
            extension = filename.rsplit(".", 1)[1].lower()
            format_name = ALLOWED_EXTENSIONS[extension]

            # ---- read file ONCE ----
            file_bytes = file.read()
            file_size = len(file_bytes)

            if file_size == 0:
                failed_files.append(filename)
                continue

            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # team_id
            cur.execute(
                "SELECT team_id FROM user_teams WHERE user_id=%s LIMIT 1",
                (user_id,)
            )
            team_id = cur.fetchone()[0]

            # duplicate check
            cur.execute("""
                SELECT 1
                FROM raw_files
                WHERE file_hash = %s
                  AND is_archived = FALSE
                LIMIT 1
            """, (file_hash,))
            if cur.fetchone():
                duplicate_files.append(filename)
                continue

            try:
                # insert raw_files
                cur.execute("""
                    INSERT INTO raw_files
                    (team_id, uploaded_by, original_name, file_size_bytes,
                     format_id, environment_id, file_hash)
                    VALUES (
                        %s, %s, %s, %s,
                        (SELECT format_id FROM file_formats WHERE format_name=%s),
                        %s, %s
                    )
                    RETURNING file_id
                """, (
                    team_id,
                    user_id,
                    filename,
                    file_size,
                    format_name,
                    environment_id,
                    file_hash
                ))

                file_id = cur.fetchone()[0]
                log_audit(f"Uploaded {filename}")
                conn.commit()

                # ---- parse logs ----
                total, inserted, skipped = run_parser(
                    file_id,
                    BytesIO(file_bytes),
                    format_name
                )

                overall_total += total
                overall_inserted += inserted

                if inserted > 0:
                    parsed_files.append(filename)
                else:
                    failed_files.append(filename)

            except Exception:
                conn.rollback()
                failed_files.append(filename)

        cur.close()
        conn.close()

        parsed_pct = int((overall_inserted / overall_total) * 100) if overall_total else 0

        return redirect(url_for(
            "upload.upload_file",
            parsed=",".join(parsed_files),
            duplicates=",".join(duplicate_files),
            failed=",".join(failed_files),
            total_logs=overall_total,
            inserted_logs=overall_inserted,
            parsed_pct=parsed_pct
        ))

    cur.close()
    conn.close()
    return render_template("upload.html", environments=environments, admin=admin)
