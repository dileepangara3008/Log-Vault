from flask import Blueprint, render_template, session, redirect, url_for, request
from db import get_db_connection

dashboard_bp = Blueprint("dashboard", __name__)

def is_admin_user(cur, user_id):
    cur.execute("""
        SELECT 1
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.role_id
        WHERE ur.user_id = %s AND r.role_name = 'ADMIN'
        LIMIT 1
    """, (user_id,))
    return cur.fetchone() is not None


@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    days = request.args.get("days", "7")
    if days not in ("7", "30", "90"):
        days = "7"

    # Admin can filter by team
    selected_team_id = request.args.get("team_id")

    # User can choose scope
    # "TEAM" = all logs uploaded by any member in the same team
    # "MINE" = only logs uploaded by me
    scope = request.args.get("scope", "TEAM")
    if scope not in ("TEAM", "MINE"):
        scope = "TEAM"

    conn = get_db_connection()
    cur = conn.cursor()

    admin = is_admin_user(cur, user_id)
    show_team_chart = admin and not selected_team_id
    # -------------------------
    # Determine allowed team_ids
    # -------------------------
    if admin:
        # Admin sees ALL teams
        cur.execute("SELECT team_id, team_name FROM teams ORDER BY team_name")
        all_teams = cur.fetchall()

        if selected_team_id:
            team_ids = [int(selected_team_id)]
        else:
            team_ids = [t[0] for t in all_teams]
    else:
        # Normal user sees only his teams
        cur.execute("""
            SELECT t.team_id, t.team_name
            FROM user_teams ut
            JOIN teams t ON ut.team_id = t.team_id
            WHERE ut.user_id = %s
            ORDER BY t.team_name
        """, (user_id,))
        user_teams = cur.fetchall()

        all_teams = []  # admin-only dropdown list
        team_ids = [t[0] for t in user_teams]

        if not team_ids:
            cur.close()
            conn.close()
            return render_template("dashboard.html", admin=admin, days=days)

    # -------------------------
    # Base WHERE filters
    # -------------------------
    where_sql = """
    WHERE rf.team_id = ANY(%s)
      AND rf.uploaded_at >= NOW() - (%s || ' days')::interval
    """
    params = [team_ids, days]


    # If user chooses "My uploads only"
    if not admin and scope == "MINE":
        where_sql += " AND rf.uploaded_by = %s"
        params.append(user_id)

    # -------------------------
    # 1) Total logs per day
    # -------------------------
    cur.execute(f"""
        SELECT DATE(le.log_timestamp) AS day, COUNT(*) AS total_logs
        FROM log_entries le
        JOIN raw_files rf ON le.file_id = rf.file_id
        {where_sql} AND rf.is_archived=FALSE
        GROUP BY day
        ORDER BY day DESC LIMIT 5
    """, params)
    logs_per_day = cur.fetchall()

    # -------------------------
    # 2) Severity summary
    # -------------------------
    cur.execute(f"""
        SELECT ls.severity_code, COUNT(*) AS count
        FROM log_entries le
        JOIN raw_files rf ON le.file_id = rf.file_id
        JOIN log_severities ls ON le.severity_id = ls.severity_id
        {where_sql} AND rf.is_archived=FALSE
        GROUP BY ls.severity_code
        ORDER BY count DESC
    """, params)
    severity_summary = cur.fetchall()

    # -------------------------
    # 3) Top error types
    # -------------------------
    cur.execute(f"""
        SELECT le.message_line, COUNT(*) AS error_count
        FROM log_entries le
        JOIN raw_files rf ON le.file_id = rf.file_id
        JOIN log_severities ls ON le.severity_id = ls.severity_id
        {where_sql} AND rf.is_archived=FALSE
          AND ls.severity_code IN ('ERROR', 'FATAL')
        GROUP BY le.message_line
        ORDER BY error_count DESC
        LIMIT 5
    """, params)
    top_errors = cur.fetchall()

    # -------------------------
    # 4) Most active systems (approx)
    # -------------------------
    cur.execute(f"""
        SELECT SUBSTRING(le.message_line FROM 1 FOR 40) AS system_key,
               COUNT(*) AS total_logs
        FROM log_entries le
        JOIN raw_files rf ON le.file_id = rf.file_id
        {where_sql} AND rf.is_archived=FALSE
        GROUP BY system_key
        ORDER BY total_logs DESC
        LIMIT 5
    """, params)
    most_active_systems = cur.fetchall()

    # -------------------------
    # 5) File Summary (NEW)
    # -------------------------
    file_where_sql = """
        WHERE rf.team_id = ANY(%s)
          AND rf.uploaded_at >= NOW() - (%s || ' days')::interval
    """
    file_params = [team_ids, days]

    # If user chooses "My uploads only"
    if not admin and scope == "MINE":
        file_where_sql += " AND rf.uploaded_by = %s"
        file_params.append(user_id)

    # -------------------------
    # File + Log Summary Cards
    # -------------------------
    cur.execute(f"""
        SELECT COUNT(*)
        FROM raw_files rf
        {file_where_sql}
        """, file_params)
    total_files = cur.fetchone()[0]


    cur.execute(f"""
        SELECT COUNT(*)
        FROM raw_files rf
        {file_where_sql}
        AND rf.is_archived = FALSE
        """, file_params)
    active_files = cur.fetchone()[0]


    cur.execute(f"""
        SELECT COUNT(*)
        FROM raw_files rf
        {file_where_sql}
        AND rf.is_archived = TRUE
        """, file_params)
    archived_files = cur.fetchone()[0]


    cur.execute(f"""
        SELECT COUNT(*)
        FROM log_entries le
        JOIN raw_files rf ON le.file_id = rf.file_id
        {where_sql} AND rf.is_archived = FALSE
        """, params)
    total_logs = cur.fetchone()[0]


    cur.execute(f"""
        SELECT 
            COALESCE(
                ROUND(COUNT(le.log_id)::numeric / NULLIF(COUNT(DISTINCT rf.file_id), 0), 2),
                0
            )
        FROM raw_files rf
        LEFT JOIN log_entries le ON le.file_id = rf.file_id
        {file_where_sql}
        AND rf.is_archived = FALSE
        """, file_params)
    avg_logs_per_file = cur.fetchone()[0]


    cur.execute(f"""
        SELECT MAX(rf.uploaded_at)
        FROM raw_files rf
        {file_where_sql}
        """, file_params)
    last_upload_time = cur.fetchone()[0]


    labels = []
    values = []

    if show_team_chart:
        cur.execute("""
            SELECT 
                t.team_name,
                COUNT(rf.file_id) AS total_files
            FROM teams t
            LEFT JOIN raw_files rf 
                ON t.team_id = rf.team_id
                AND rf.uploaded_at >= NOW() - (%s || ' days')::interval
                AND rf.is_archived = FALSE
            GROUP BY t.team_name
            ORDER BY t.team_name
            """, (days,))

    rows = cur.fetchall()
    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]

    cur.execute(f"""
        SELECT 
            DATE(rf.uploaded_at) AS day,
            COUNT(*) AS total_files
        FROM raw_files rf
        {file_where_sql} AND 
        rf.is_archived = FALSE
        GROUP BY day
        ORDER BY day ASC
        """, file_params)

    files_per_day = cur.fetchall()
    print(files_per_day)

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        admin=admin,
        days=days,
        scope=scope,
        all_teams=all_teams,
        selected_team_id=selected_team_id,
        logs_per_day=logs_per_day,
        severity_summary=severity_summary,
        top_errors=top_errors,
        most_active_systems=most_active_systems,

        total_files=total_files,
        active_files=active_files,
        archived_files=archived_files,
        total_logs=total_logs,
        avg_logs_per_file=avg_logs_per_file,
        last_upload_time=last_upload_time,
        labels=labels,
        values=values,
        show_team_chart=show_team_chart,
        files_per_day=files_per_day
    )

