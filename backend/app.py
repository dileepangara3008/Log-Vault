from flask import Flask, redirect, url_for, render_template
from auth import auth_bp
from dashboard import dashboard_bp
from config import SECRET_KEY
from upload import upload_bp
from logs import logs_bp

from admin import admin_bp
from user_home import user_home_bp
from files import files_bp
from profile import profile_bp


app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_home_bp)
app.register_blueprint(files_bp)
app.register_blueprint(profile_bp)



@app.route("/")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    app.run(debug=True)
