import os
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

load_dotenv()

# We store the SETTINGS here, we do not connect yet
DB_SETTINGS = {
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "host": os.getenv("host"),
    "port": os.getenv("port"),
    "database": os.getenv("dbname") 
}

SECRET_KEY = os.getenv("SECRET_KEY")