from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from db import get_db_connection
from queries import (
    GET_ADMIN_NAME,
    GET_ALL_USERS,
    INSERT_ADMIN_USER,
    INSERT_USER_CREDENTIALS,
    INSERT_USER_TEAM,
    INSERT_USER_ROLE,
    TOGGLE_USER_ACTIVE,
    GET_USERNAME,
    GET_SECURITY_LOGS,
    SOFT_DELETE_USER,
    RESTORE_USER,
    GET_TEAMS,
    GET_ROLES
)
from audit import log_audit
import bcrypt

admin_bp = Blueprint("admin", __name__)


def require_admin():
    if not session.get("user_id"):
        abort(401)
    if not session.get("is_admin", False):
        abort(403)


# =====================================================
# ADMIN HOME
# =====================================================

@admin_bp.route("/admin/home")
def admin_home():
    require_admin()

    user_id = session.get("user_id")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(GET_ADMIN_NAME, (user_id,))
    name = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "admin_home.html",
        name=name[0].upper() if name else "User"
    )


# =====================================================
# LIST USERS
# =====================================================

@admin_bp.route("/admin/users")
def list_users():
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(GET_ALL_USERS)
    users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_users.html", users=users)


# =====================================================
# CREATE USER
# =====================================================

@admin_bp.route("/admin/users/create", methods=["GET", "POST"])
def create_user():
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    #  Fetch dropdown data FIRST
    cur.execute(GET_TEAMS)
    teams = cur.fetchall()

    cur.execute(GET_ROLES)
    roles = cur.fetchall()

    if request.method == "POST":
        data = request.form

        password_hash = bcrypt.hashpw(
            data["password"].encode(),
            bcrypt.gensalt()
        ).decode()

        cur.execute(INSERT_ADMIN_USER, (
            data["first_name"],
            data.get("last_name"),
            data["phone_no"],
            data["email"],
            data["username"],
            password_hash,
            data["gender"]
        ))

        new_user_id = cur.fetchone()[0]

        cur.execute(INSERT_USER_CREDENTIALS, (new_user_id,))
        cur.execute(INSERT_USER_TEAM, (new_user_id, data["team_id"]))
        cur.execute(INSERT_USER_ROLE, (new_user_id, data["role_id"]))

        conn.commit()

        log_audit(f"Created user {data['email']}")

        cur.close()
        conn.close()

        return redirect(url_for("admin.list_users"))

    cur.close()
    conn.close()

    return render_template(
        "admin_create_user.html",
        teams=teams,
        roles=roles
    )


@admin_bp.route("/admin/users/<int:user_id>/profile")
def admin_view_user_profile(user_id):
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, first_name, last_name, phone_no,
               email, username, gender,
               is_active, is_deleted,
               to_char(created_at ,'YYYY-MM-DD HH24:MI:SS')
        FROM users
        WHERE user_id = %s
    """, (user_id,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        abort(404, "User not found")

    return render_template("admin_user_profile.html", user=user)


@admin_bp.route("/admin/users/<int:user_id>/profile/edit", methods=["GET", "POST"])
def admin_edit_user_profile(user_id):
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch dropdowns
    cur.execute(GET_TEAMS)
    teams = cur.fetchall()

    cur.execute(GET_ROLES)
    roles = cur.fetchall()

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
        cur.close()
        conn.close()

        return redirect(
            url_for("admin.admin_view_user_profile", user_id=user_id)
        )

    # GET user data
    cur.execute("""
        SELECT user_id, first_name, last_name, phone_no,
               email, username, gender
        FROM users
        WHERE user_id = %s
    """, (user_id,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        abort(404)

    return render_template(
        "admin_edit_user_profile.html",
        user=user,
        teams=teams,
        roles=roles
    )



# =====================================================
# TOGGLE ACTIVE
# =====================================================

@admin_bp.route("/admin/users/<int:user_id>/toggle_active")
def toggle_active(user_id):
    require_admin()

    if user_id == session.get("user_id"):
        abort(403, "Admin cannot toggle himself")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(TOGGLE_USER_ACTIVE, (user_id,))
    row = cur.fetchone()

    if not row:
        abort(404, "User not found")

    new_status = row[0]

    cur.execute(GET_USERNAME, (user_id,))
    username = cur.fetchone()[0]

    conn.commit()

    log_audit(
        f"user {username} {'activated' if new_status else 'inactivated'}"
    )

    cur.close()
    conn.close()

    return redirect(url_for("admin.list_users"))


# =====================================================
# SECURITY LOGS
# =====================================================

@admin_bp.route("/admin/security-logs")
def view_security_logs():
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(GET_SECURITY_LOGS)
    logs = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_security_logs.html", logs=logs)


# =====================================================
# DELETE / RESTORE USER
# =====================================================

@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    require_admin()

    if user_id == session.get("user_id"):
        abort(403)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(SOFT_DELETE_USER, (user_id,))
    conn.commit()

    log_audit(f"Deleted user {user_id}")

    cur.close()
    conn.close()

    return redirect(url_for("admin.list_users"))


@admin_bp.route("/admin/users/<int:user_id>/restore", methods=["POST"])
def restore_user(user_id):
    require_admin()

    if user_id == session.get("user_id"):
        abort(403)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(RESTORE_USER, (user_id,))
    conn.commit()

    log_audit(f"Restored user {user_id}")

    cur.close()
    conn.close()

    return redirect(url_for("admin.list_users"))
