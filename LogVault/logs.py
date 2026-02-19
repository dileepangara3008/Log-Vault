from flask import Blueprint, render_template, request, session, redirect, url_for
from db import get_db_connection
from audit import log_audit
from permissions import require_permission
from queries import (
    GET_MIN_MAX_UPLOAD_DATE,  
    GET_ALL_TEAMS,
    GET_USER_TEAM_IDS,
    GET_SEVERITIES,
    GET_CATEGORIES,
    GET_ENVIRONMENTS,
    CHECK_ADMIN
)

logs_bp = Blueprint("logs", __name__)

@logs_bp.route("/logs", methods=["GET"])
@require_permission("VIEW_LOG")
def view_logs():
    """
    To view all the logs inserted in log entries table and apply certain filters required
    """
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    # -----------------------
    # Read filters
    # -----------------------
    keyword = request.args.get("q", "").strip()
    severity = request.args.get("severity")
    category = request.args.get("category")
    environment = request.args.get("environment")

    # User scope filter (TEAM / MINE)
    scope = request.args.get("scope", "TEAM")
    if scope not in ("TEAM", "MINE"):
        scope = "TEAM"

    # Admin team filter
    selected_team_id = request.args.get("team_id")

    page = int(request.args.get("page", 1))
    limit = 20
    offset = (page - 1) * limit

    conn = get_db_connection()
    cur = conn.cursor()

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    cur.execute(GET_MIN_MAX_UPLOAD_DATE)
    min_date, max_date = cur.fetchone()

    # ---- Apply defaults ONLY if missing ----
    if not start_date and min_date:
        start_date = min_date.strftime("%Y-%m-%d")

    if not end_date and max_date:
        end_date = max_date.strftime("%Y-%m-%d")

    # -----------------------
    # Check if ADMIN
    # -----------------------
    cur.execute(CHECK_ADMIN, (user_id,))
    is_admin = cur.fetchone() is not None

    # -----------------------
    # Decide team_ids scope
    # -----------------------
    all_teams = []

    if is_admin:
        cur.execute(GET_ALL_TEAMS)
        all_teams = cur.fetchall()

        if selected_team_id:
            team_ids = [int(selected_team_id)]
        else:
            team_ids = [t[0] for t in all_teams]
    else:
        cur.execute(GET_USER_TEAM_IDS, (user_id,))
        team_ids = [row[0] for row in cur.fetchall()]

    if not team_ids:
        cur.close()
        conn.close()
        return render_template("logs.html", logs=[], admin=is_admin)

    # -----------------------
    # Base query
    # -----------------------
    query = """
        SELECT
            to_char(le.log_timestamp, 'YYYY-MM-DD HH24:MI:SS'),
            ls.severity_code,
            lc.category_name,
            e.environment_code,
            le.message_line,
            rf.original_name,
            concat(u.first_name,' ', u.last_name)
        FROM log_entries le
        JOIN log_severities ls ON le.severity_id = ls.severity_id
        JOIN log_categories lc ON le.category_id = lc.category_id
        JOIN raw_files rf ON le.file_id = rf.file_id
        JOIN environments e ON rf.environment_id = e.environment_id
        JOIN users u on rf.uploaded_by = u.user_id
        WHERE rf.team_id = ANY(%s) AND rf.is_archived=FALSE
    """
    params = [team_ids]

    # -----------------------
    # User Scope (My Logs Only)
    # -----------------------
    if not is_admin and scope == "MINE":
        query += " AND rf.uploaded_by = %s"
        params.append(user_id)

    # -----------------------
    # Apply filters
    # -----------------------
    if keyword:
        query += " AND le.message_line ILIKE %s"
        params.append(f"%{keyword}%")

    if severity:
        query += " AND ls.severity_code = %s"
        params.append(severity)

    if category:
        query += " AND lc.category_name = %s"
        params.append(category)

    if environment:
        query += " AND e.environment_code = %s"
        params.append(environment)

    if start_date:
        query += " AND DATE(le.log_timestamp) >= %s"
        params.append(start_date)

    if end_date:
        query += " AND DATE(le.log_timestamp) <= %s"
        params.append(end_date)

    query += """
        ORDER BY le.log_timestamp DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    cur.execute(query, params)
    logs = cur.fetchall()

    # -----------------------
    # Filter dropdown options
    # -----------------------
    cur.execute(GET_SEVERITIES)
    severities = [r[0] for r in cur.fetchall()]

    cur.execute(GET_CATEGORIES)
    categories = [r[0] for r in cur.fetchall()]

    cur.execute(GET_ENVIRONMENTS)
    environments = [r[0] for r in cur.fetchall()]

    # log_audit("VIEW_LOGS", "log_entries", None, f"scope={scope}, q={keyword}")

    cur.close()
    conn.close()

    return render_template(
        "logs.html",
        logs=logs,
        severities=severities,
        categories=categories,
        environments=environments,
        page=page,
        admin=is_admin,
        all_teams=all_teams,
        selected_team_id=selected_team_id,
        keyword=keyword,
        severity=severity,
        category=category,
        environment=environment,
        start_date=start_date,
        scope=scope,
        end_date=end_date
    )   
