from flask import Blueprint, render_template, request, session, redirect, url_for
from db import get_db_connection
from audit import log_audit

profile_bp = Blueprint("profile", __name__)

# =====================================================
# VIEW PROFILE
# =====================================================
@profile_bp.route("/profile")
def view_profile():
    """
    Any logged in user can view profile
    """
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            u.user_id,
            u.first_name,
            u.last_name,
            u.phone_no,
            u.email,
            u.username,
            u.gender,
            to_char(u.created_at,'YYYY-MM-DD HH24:MI:SS') AS created_at,
            t.team_name
        FROM users u
        LEFT JOIN user_teams ut ON ut.user_id = u.user_id
        LEFT JOIN teams t ON t.team_id = ut.team_id
        WHERE u.user_id = %s
    """, (user_id,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return redirect(url_for("auth.logout"))

    columns = [desc[0] for desc in cur.description]
    user = dict(zip(columns, row))

    cur.close()
    conn.close()

    return render_template(
        "profile.html",
        user=user
    )

# =====================================================
# EDIT PROFILE
# =====================================================
@profile_bp.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    """
    Any logged in user can edit their profiles
    """
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form.get("last_name")
        phone_no = request.form["phone_no"]
        username = request.form.get("username")
        gender = request.form["gender"]

        cur.execute("""
            UPDATE users
            SET first_name=%s,
                last_name=%s,
                phone_no=%s,
                username=%s,
                gender=%s,
                updated_at=NOW()
            WHERE user_id=%s
        """, (first_name, last_name, phone_no, username, gender, user_id))

        conn.commit()

        log_audit("User updated profile")

        cur.close()
        conn.close()

        return redirect(url_for("profile.view_profile"))

    # GET request
    cur.execute("""
        SELECT first_name, last_name, phone_no, email, username, gender
        FROM users
        WHERE user_id = %s
    """, (user_id,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return redirect(url_for("auth.logout"))

    columns = [desc[0] for desc in cur.description]
    user = dict(zip(columns, row))

    cur.close()
    conn.close()

    return render_template(
        "edit_profile.html",
        user=user
    )
