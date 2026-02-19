from flask import Blueprint, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.utils import secure_filename
import hashlib
from io import BytesIO
from db import get_db_connection
from queries import (
    CHECK_ADMIN,
    GET_TEAM_ID,
    GET_EXISTING_HASHES,
    INSERT_RAW_FILE,
    INSERT_FILE_PARSE_STATS
)
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
    """
    To check whether the file is in allowed extensions
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

#===================================
#======FILE UPLOAD
#=================================
@upload_bp.route("/upload", methods=["GET", "POST"])
@require_permission("UPLOAD_LOG")
def upload_file():
    """
    File uploading
    """
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    #  Admin check 
    cur.execute(CHECK_ADMIN, (user_id,))
    admin = cur.fetchone() is not None

    #  Get environments 
    cur.execute("select environment_id, environment_code from environments")
    environments = cur.fetchall()

    if request.method == "POST":
        parsed_files = []
        duplicate_files = []
        failed_files = []
        unsupported = []
        overall_total = 0
        overall_inserted = 0

        files = request.files.getlist("files")
        environment_id = request.form.get("environment_id")

        if not environment_id:
            abort(400, "Environment is required")

        #  Fetch team_id ONCE 
        cur.execute(GET_TEAM_ID, (user_id,))
        team_row = cur.fetchone()
        if not team_row:
            abort(400, "User not assigned to team")

        team_id = team_row[0]

        #  Prefetch all existing hashes ONCE
        cur.execute(GET_EXISTING_HASHES)
        existing_hashes = {row[0] for row in cur.fetchall()}

        for file in files:

            if not file or file.filename == "":
                continue

            if not allowed_file(file.filename):
                unsupported.append(file.filename)
                continue

            filename = secure_filename(file.filename)
            extension = filename.rsplit(".", 1)[1].lower()
            format_name = ALLOWED_EXTENSIONS[extension]

            file_bytes = file.read()
            file_size = len(file_bytes)

            if file_size == 0:
                failed_files.append(filename)
                continue

            file_hash = hashlib.sha256(file_bytes).hexdigest()

            #  Duplicate check 
            if file_hash in existing_hashes:
                duplicate_files.append(filename)
                continue

            try:
                # Insert raw file
                cur.execute(INSERT_RAW_FILE, (
                    team_id,
                    user_id,
                    filename,
                    file_size,
                    format_name,
                    environment_id,
                    file_hash
                ))

                file_id = cur.fetchone()[0]

                conn.commit()

                # Run parser
                total, inserted, skipped = run_parser(
                    file_id,
                    BytesIO(file_bytes),
                    format_name
                )

                overall_total += total
                overall_inserted += inserted

                parsed_percentage = int((inserted / total) * 100) if total else 0

                # Insert stats
                cur.execute(INSERT_FILE_PARSE_STATS, (
                    file_id,
                    total,
                    inserted,
                    skipped,
                    parsed_percentage
                ))

                log_audit(f"Uploaded {filename}")
                conn.commit()

                # Classification
                if total == 0 or inserted == 0:
                    failed_files.append(filename)
                else:
                    parsed_files.append(filename)

                # Add hash to set (avoid duplicates within same batch)
                existing_hashes.add(file_hash)

            except Exception as e:
                conn.rollback()
                print("UPLOAD ERROR:", e)
                failed_files.append(filename)

        cur.close()
        conn.close()

        parsed_pct = int((overall_inserted / overall_total) * 100) if overall_total else 0

        if unsupported:
            flash(f"Unsupported files skipped: {', '.join(unsupported)}", "warning")

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
