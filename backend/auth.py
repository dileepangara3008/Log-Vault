from datetime import datetime, timedelta
import bcrypt
from db import get_db_connection
from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_jwt_extended import create_access_token
from permissions import get_user_permissions
import re



auth_bp = Blueprint("auth", __name__)

LOCK_LIMIT = 3

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch teams
    cur.execute("SELECT team_id, team_name FROM teams")
    teams = cur.fetchall()

    # Fetch roles
    cur.execute("SELECT role_id, role_name FROM roles")
    roles = cur.fetchall()

    if request.method == "POST":
        data = request.form

        email_error = validate_email(data["email"])
        if email_error:
            cur.close()
            conn.close()
            return render_template("register.html", teams=teams, roles=roles, error=email_error)

        phone_error = validate_phone(data["phone_no"])
        if phone_error:
            cur.close()
            conn.close()
            return render_template("register.html", teams=teams, roles=roles, error=phone_error)

        # confirm password check
        if data["password"] != data["confirm_password"]:
            cur.close()
            conn.close()
            return render_template("register.html", teams=teams, roles=roles, error="Passwords do not match")

        # strong password check
        password_error = validate_password(data["password"])
        if password_error:
            cur.close()
            conn.close()
            return render_template("register.html", teams=teams, roles=roles, error=password_error)


        password_hash = bcrypt.hashpw(
            data["password"].encode(), bcrypt.gensalt()
        ).decode()

        # Insert user
        cur.execute("""
            INSERT INTO users
            (first_name, last_name, phone_no, email, username, password_hash, gender)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING user_id
        """, (
            data["first_name"],
            data.get("last_name"),
            data["phone_no"],
            data["email"],
            data.get("username"),
            password_hash,
            data["gender"]
        ))

        user_id = cur.fetchone()[0]

        # user_credentials
        cur.execute("""
            INSERT INTO user_credentials (user_id)
            VALUES (%s)
        """, (user_id,))

        # user_roles (selected role)
        cur.execute("""
            INSERT INTO user_roles (user_id, role_id)
            VALUES (%s, %s)
        """, (user_id, int(data["role_id"])))

        # user_teams
        cur.execute("""
            INSERT INTO user_teams (user_id, team_id)
            VALUES (%s, %s)
        """, (user_id, int(data["team_id"])))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("auth.login"))

    cur.close()
    conn.close()
    return render_template("register.html", teams=teams, roles=roles)


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
    # Simple & effective email validation
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(pattern, email):
        return "Invalid email format"
    return None


def validate_phone(phone: str):
    # Accepts:
    # 10 digit numbers (India)
    # +91xxxxxxxxxx
    phone = phone.strip()

    if phone.startswith("+91"):
        phone = phone[3:].strip()

    if not phone.isdigit():
        return "Phone number must contain only digits"

    if len(phone) != 10:
        return "Phone number must be exactly 10 digits"

    return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT u.user_id, u.password_hash, u.is_active, u.is_deleted,
                   COALESCE(c.failed_attempts, 0) AS failed_attempts,
                   COALESCE(c.is_locked, FALSE) AS is_locked,
                   c.locked_until
            FROM users u
            LEFT JOIN user_credentials c ON u.user_id = c.user_id
            WHERE u.email = %s
        """, (email,))

        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return render_template("login.html", error="Invalid credentials")

        user_id, pw_hash, active, deleted, attempts, locked, locked_until = row

        # if credentials row missing, create it now
        cur.execute("SELECT 1 FROM user_credentials WHERE user_id=%s", (user_id,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO user_credentials (user_id) VALUES (%s)", (user_id,))
            conn.commit()

        if not active or deleted:
            cur.close()
            conn.close()
            return render_template("login.html", error="Account disabled")

        if locked and locked_until and locked_until > datetime.utcnow():
            cur.close()
            conn.close()
            return render_template("login.html", error="Account locked")

        # Password check
        if not bcrypt.checkpw(password.encode(), pw_hash.encode()):
            attempts += 1
            cur.execute("""
                UPDATE user_credentials
                SET failed_attempts=%s,
                    last_failed_at=NOW(),
                    is_locked=%s,
                    locked_until=%s
                WHERE user_id=%s
            """, (
                attempts,
                attempts >= LOCK_LIMIT,
                datetime.utcnow() + timedelta(minutes=15) if attempts >= LOCK_LIMIT else None,
                user_id
            ))
            conn.commit()
            cur.close()
            conn.close()
            return render_template("login.html", error="Invalid credentials")

        # Success reset
        cur.execute("""
            UPDATE user_credentials
            SET failed_attempts=0,
                is_locked=FALSE,
                locked_until=NULL
            WHERE user_id=%s
        """, (user_id,))

        conn.commit()

        # Session
        session["user_id"] = user_id
        session["permissions"] = get_user_permissions(user_id)

        # Admin check
        cur.execute("""
            SELECT 1
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.role_id
            WHERE ur.user_id = %s AND r.role_name = 'ADMIN'
            LIMIT 1
        """, (user_id,))
        is_admin = cur.fetchone() is not None
        session["is_admin"] = is_admin

        cur.close()
        conn.close()

        if is_admin:
            return redirect(url_for("admin.admin_home"))
        else:
            return redirect(url_for("user_home.home"))


    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

