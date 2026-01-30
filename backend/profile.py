from flask import Blueprint, render_template, request, session, redirect, url_for
from db import get_db_connection
from audit import log_audit

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/profile")
def view_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
                select team_id from user_teams where user_id=%s
                """,(user_id,))
    team=cur.fetchone()[0]

    cur.execute("""
                select team_name from teams where team_id=%s
            """,(team,))
    team_name=cur.fetchone()[0]

    cur.execute("""
        SELECT user_id, first_name, last_name, phone_no, email, username, gender, created_at
        FROM users
        WHERE user_id = %s
    """, (user_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("profile.html", user=user, team_name=team_name)


@profile_bp.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
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

        log_audit("UPDATE_PROFILE", "users", user_id, "User updated profile")

        cur.close()
        conn.close()

        return redirect(url_for("profile.view_profile"))

    cur.execute("""
        SELECT first_name, last_name, phone_no, email, username, gender
        FROM users
        WHERE user_id = %s
    """, (user_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("edit_profile.html", user=user)
