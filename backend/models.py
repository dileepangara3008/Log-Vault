from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.BigInteger, primary_key=True)
    first_name = db.Column(db.Text, nullable=False)
    last_name = db.Column(db.Text)
    phone_no = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    gender = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserCredential(db.Model):
    __tablename__ = "user_credentials"

    credential_id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.user_id"), unique=True)
    failed_attempts = db.Column(db.Integer, default=0)
    last_failed_at = db.Column(db.DateTime)
    is_locked = db.Column(db.Boolean, default=False)
    locked_until = db.Column(db.DateTime)
    password_set_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserRole(db.Model):
    __tablename__ = "user_roles"

    user_id = db.Column(db.BigInteger, db.ForeignKey("users.user_id"), primary_key=True)
    role_id = db.Column(db.SmallInteger, primary_key=True)

class UserTeam(db.Model):
    __tablename__ = "user_teams"

    user_id = db.Column(db.BigInteger, db.ForeignKey("users.user_id"), primary_key=True)
    team_id = db.Column(db.BigInteger, primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class RawFile(db.Model):
    __tablename__ = "raw_files"

    file_id = db.Column(db.BigInteger, primary_key=True)
    team_id = db.Column(db.BigInteger)
    uploaded_by = db.Column(db.BigInteger)
    is_archived = db.Column(db.Boolean, default=False)
