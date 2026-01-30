from flask import Blueprint, render_template, session, redirect, url_for
from db import get_db_connection

user_home_bp = Blueprint("user_home", __name__)

@user_home_bp.route("/home")
def home():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT CONCAT(first_name, ' ', last_name) FROM users WHERE user_id = %s",
        (user_id,)
    )
    name = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("user_home.html", name=name[0] if name else "User")

