from datetime import datetime, timedelta, timezone
import bcrypt
import re
from flask import Blueprint, render_template, request, redirect, url_for, session
from db import get_db_connection
from queries import (
    GET_TEAMS,
    GET_ROLES,
    INSERT_USER,
    INSERT_USER_CREDENTIALS,
    INSERT_USER_ROLE,
    INSERT_USER_TEAM,
    GET_USER_FOR_LOGIN,
    UPDATE_FAILED_ATTEMPTS,
    RESET_FAILED_ATTEMPTS,
    GET_USER_ROLES_AND_PERMISSIONS
)

auth_bp = Blueprint("auth", __name__)

LOCK_LIMIT = 3


# =====================================================
# REGISTER
# =====================================================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch dropdown data 
    cur.execute(GET_TEAMS)
    teams = cur.fetchall()

    cur.execute(GET_ROLES)
    roles = cur.fetchall()

    if request.method == "POST":
        data = request.form

        # Validation
        email_error = validate_email(data["email"])
        if email_error:
            return render_template("register.html", teams=teams, roles=roles, error=email_error)

        phone_error = validate_phone(data["phone_no"])
        if phone_error:
            return render_template("register.html", teams=teams, roles=roles, error=phone_error)

        if data["password"] != data["confirm_password"]:
            return render_template("register.html", teams=teams, roles=roles, error="Passwords do not match")

        password_error = validate_password(data["password"])
        if password_error:
            return render_template("register.html", teams=teams, roles=roles, error=password_error)

        try:
            password_hash = bcrypt.hashpw(
                data["password"].encode(),
                bcrypt.gensalt()
            ).decode()

            # Insert user
            cur.execute(INSERT_USER, (
                data["first_name"],
                data.get("last_name"),
                data["phone_no"],
                data["email"],
                data.get("username"),
                password_hash,
                data["gender"]
            ))

            user_id = cur.fetchone()[0]

            # Insert related records
            cur.execute(INSERT_USER_CREDENTIALS, (user_id,))
            cur.execute(INSERT_USER_ROLE, (user_id, int(data["role_id"])))
            cur.execute(INSERT_USER_TEAM, (user_id, int(data["team_id"])))

            conn.commit()

        except Exception as e:
            conn.rollback()
            return render_template("register.html", teams=teams, roles=roles, error="Registration failed")

        finally:
            cur.close()
            conn.close()

        return redirect(url_for("auth.login"))

    cur.close()
    conn.close()
    return render_template("register.html", teams=teams, roles=roles)


# =====================================================
# LOGIN
# =====================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(GET_USER_FOR_LOGIN, (email,))
        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            return render_template("login.html", error="Invalid credentials")

        user_id, pw_hash, active, deleted, attempts, locked, locked_until = row

        if not active or deleted:
            cur.close()
            conn.close()
            return render_template("login.html", error="Account disabled")

        if locked and locked_until and locked_until > datetime.now(timezone.utc):
            cur.close()
            conn.close()
            return render_template("login.html", error="Account locked")

        # Password check
        if not bcrypt.checkpw(password.encode(), pw_hash.encode()):
            attempts += 1

            cur.execute(UPDATE_FAILED_ATTEMPTS, (
                attempts,
                attempts >= LOCK_LIMIT,
                datetime.utcnow() + timedelta(minutes=15) if attempts >= LOCK_LIMIT else None,
                user_id
            ))

            conn.commit()
            cur.close()
            conn.close()

            return render_template("login.html", error="Invalid credentials")

        # Reset attempts on success
        cur.execute(RESET_FAILED_ATTEMPTS, (user_id,))
        conn.commit()

        # Fetch roles + permissions in single query
        cur.execute(GET_USER_ROLES_AND_PERMISSIONS, (user_id,))
        rows = cur.fetchall()

        permissions = set()
        is_admin = False

        for role_name, permission_name in rows:
            if role_name == "ADMIN":
                is_admin = True
            if permission_name:
                permissions.add(permission_name)

        session["user_id"] = user_id
        session["permissions"] = list(permissions)
        session["is_admin"] = is_admin

        cur.close()
        conn.close()

        if is_admin:
            return redirect(url_for("admin.admin_home"))
        else:
            return redirect(url_for("user_home.home"))

    return render_template("login.html")


# =====================================================
# LOGOUT
# =====================================================

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# =====================================================
# VALIDATION HELPERS
# =====================================================

def validate_password(password: str):
    if len(password) < 8:
        return "Password must be at least 8 characters long"

    if " " in password:
        return "Password must not contain spaces"

    if not re.search(r"[A-Z]", password):
        return "Password must contain at least 1 uppercase letter"

    if not re.search(r"[a-z]", password):
        return "Password must contain at least 1 lowercase letter"

    if not re.search(r"[0-9]", password):
        return "Password must contain at least 1 digit"

    if not re.search(r"[@$!%*?&^#()_\-+=<>/\\{}\[\].,;:]", password):
        return "Password must contain at least 1 special character"

    return None


def validate_email(email: str):
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(pattern, email):
        return "Invalid email format"
    return None


def validate_phone(phone: str):
    phone = phone.strip()

    if phone.startswith("+91"):
        phone = phone[3:].strip()

    if not phone.isdigit():
        return "Phone number must contain only digits"

    if len(phone) != 10:
        return "Phone number must be exactly 10 digits"

    return None
