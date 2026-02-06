from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from db import get_db_connection
from audit import log_audit
from werkzeug.security import generate_password_hash
from permissions import require_permission
import bcrypt


admin_bp = Blueprint("admin", __name__)

def require_admin():
    user_id = session.get("user_id")
    if not user_id:
        abort(401)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.role_id
        WHERE ur.user_id = %s AND r.role_name = 'ADMIN'
        LIMIT 1
    """, (user_id,))

    ok = cur.fetchone() is not None
    cur.close()
    conn.close()

    if not ok:
        abort(403)

@admin_bp.route("/admin/home")
def admin_home():
    user_id = session.get("user_id")
    if not user_id:
        abort(401)
        
    require_admin()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT CONCAT(first_name, ' ', last_name) FROM users WHERE user_id = %s",
        (user_id,)
    )

    name = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("admin_home.html",name=name[0].upper() if name else "User")

@admin_bp.route("/admin/users")
@require_permission("MANAGE_USERS")
def list_users():
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, first_name, last_name, email, username, is_active, is_deleted, created_at
        FROM users
        ORDER BY created_at DESC
    """)
    users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_users.html", users=users)


@admin_bp.route("/admin/users/create", methods=["GET", "POST"])
def create_user():
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    # Load teams and roles
    cur.execute("SELECT team_id, team_name FROM teams ORDER BY team_name")
    teams = cur.fetchall()

    cur.execute("SELECT role_id, role_name FROM roles ORDER BY role_name")
    roles = cur.fetchall()

    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form.get("last_name")
        phone_no = request.form["phone_no"]
        gender = request.form["gender"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        team_id = request.form["team_id"]
        role_id = request.form["role_id"]

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Insert into users
        cur.execute("""
            INSERT INTO users (first_name, last_name, phone_no, email, username, password_hash, gender)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING user_id
        """, (first_name, last_name, phone_no, email, username, password_hash, gender))

        new_user_id = cur.fetchone()[0]

        cur.execute("INSERT INTO user_credentials (user_id) VALUES (%s)", (new_user_id,))

        # Assign team
        cur.execute("""
            INSERT INTO user_teams (user_id, team_id)
            VALUES (%s, %s)
        """, (new_user_id, team_id))

        # Assign role
        cur.execute("""
            INSERT INTO user_roles (user_id, role_id)
            VALUES (%s, %s)
        """, (new_user_id, role_id))

        conn.commit()

        log_audit(f"Created user {email}")

        cur.close()
        conn.close()
        return redirect(url_for("admin.list_users"))

    cur.close()
    conn.close()
    return render_template("admin_create_user.html", teams=teams, roles=roles)


@admin_bp.route("/admin/users/<int:user_id>/toggle_active")
def toggle_active(user_id):
    require_admin()

    current_admin_id = session.get("user_id")

    # ❌ Block admin from toggling himself
    if user_id == current_admin_id:
        abort(403, "Admin cannot toggle his own account")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET is_active = NOT is_active,
            updated_at = NOW()
        WHERE user_id = %s
        RETURNING is_active
    """, (user_id,))
    row = cur.fetchone()
    if not row:
        abort(404, "User not found")

    new_status = row[0]

    # Get target username
    cur.execute(
    "SELECT username FROM users WHERE user_id = %s",
    (user_id,)
)
    username = cur.fetchone()[0]

    # Audit message
    if new_status:
        log_audit(f"user {username} activated")
    else:
        log_audit(f"user {username} inactivated")

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/admin/security-logs")
def view_security_logs():
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
            SELECT
                a.action_id,
                u.username,
                a.action_type,
                DATE(a.action_time)
            FROM audit_trail a
            JOIN users u ON u.user_id = a.user_id
            ORDER BY a.action_time DESC
    """)

    logs = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_security_logs.html", logs=logs)


@admin_bp.route("/admin/users/<int:user_id>/profile")
def admin_view_user_profile(user_id):
    require_admin()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, first_name, last_name, phone_no, email, username, gender, is_active, is_deleted, created_at
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

    # Fetch all teams (for dropdown)
    cur.execute("SELECT team_id, team_name FROM teams")
    teams = cur.fetchall()

    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form.get("last_name")
        phone_no = request.form["phone_no"]
        username = request.form.get("username")
        gender = request.form["gender"]
        team_id = request.form.get("team_id")

        cur.execute("""
            UPDATE users
            SET first_name = %s,
                last_name = %s,
                phone_no = %s,
                username = %s,
                gender = %s,
                updated_at = NOW()
            WHERE user_id = %s
            """, (
            first_name,
            last_name,
            phone_no,
            username,
            gender,
            user_id
        ))

        cur.execute("""
            UPDATE user_teams
            SET team_id = %s
            WHERE user_id = %s
        """, (int(team_id), user_id))

        conn.commit()

        conn.commit()

        log_audit(
            f"Admin updated user_id={user_id}"
        )

        cur.close()
        conn.close()

        return redirect(
            url_for("admin.admin_view_user_profile", user_id=user_id)
        )

    # ---------- GET REQUEST ----------
    # Fetch user details
    cur.execute("""
        SELECT user_id,
               first_name,
               last_name,
               phone_no,
               email,
               username,
               gender,
               is_active,
               is_deleted
        FROM users
        WHERE user_id = %s
    """, (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        abort(404, "User not found")

    # Fetch user's team
    cur.execute("""
        SELECT user_id, team_id
        FROM user_teams
        WHERE user_id = %s
    """, (user_id,))
    team1 = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "admin_edit_user_profile.html",
        user=user,
        teams=teams,
        team1=team1
    )

@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    require_admin()

    if user_id == session.get("user_id"):
        abort(403, "Admin cannot delete himself")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET is_deleted = TRUE,
            is_active = FALSE,
            updated_at = NOW()
        WHERE user_id = %s
    """, (user_id,))
    conn.commit()

    log_audit(f"deleted user of user id {user_id}")

    cur.close()
    conn.close()
    return redirect(url_for("admin.list_users"))

@admin_bp.route("/admin/users/<int:user_id>/restore", methods=["POST"])
def restore_user(user_id):
    require_admin()

    if user_id == session.get("user_id"):
        abort(403, "Admin cannot restore himself")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET is_deleted = FALSE,
            is_active = TRUE,
            updated_at = NOW()
        WHERE user_id = %s
    """, (user_id,))
    conn.commit()

    log_audit(f"Restored user of user id {user_id}")

    cur.close()
    conn.close()
    return redirect(url_for("admin.list_users"))
