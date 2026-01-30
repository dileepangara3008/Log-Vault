import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
# MAX_CONTENT_LENGTH = 20 * 1024 * 1024  

DB_CONFIG = {
    "dbname": "log_management",
    "user": "postgres",
    "password": "techv1@3",
    "host": "localhost",
    "port": 5432
}

SECRET_KEY = "secret-key"
