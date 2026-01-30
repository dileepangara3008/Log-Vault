import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
# MAX_CONTENT_LENGTH = 20 * 1024 * 1024  

# DB_CONFIG = {
#     "dbname": "log_management",
#     "user": "postgres",
#     "password": "techv1@3",
#     "host": "localhost",
#     "port": 5432
# }

# SECRET_KEY = "secret-key"


# import psycopg2
# from dotenv import load_dotenv

# # Load environment variables from .env
# load_dotenv()

# # Fetch variables
# USER = os.getenv("user")
# PASSWORD = os.getenv("password")
# HOST = os.getenv("host")
# PORT = os.getenv("port")
# DBNAME = os.getenv("dbname")
# SECRET_KEY = os.getenv("SECRET_KEY")

# # Connect to the database
# try:
#     DB_CONFIG = psycopg2.connect(
#         user=USER,
#         password=PASSWORD,
#         host=HOST,
#         port=PORT,
#         dbname=DBNAME
#     )
#     print("Connection successful!")
    
#     # Create a cursor to execute SQL queries
#     cursor = DB_CONFIG.cursor()
    
#     # Example query
#     cursor.execute("SELECT NOW();")
#     result = cursor.fetchone()
#     print("Current Time:", result)

#     # Close the cursor and connection
#     cursor.close()
#     DB_CONFIG.close()
#     print("Connection closed.")

# except Exception as e:
#     print(f"Failed to connect: {e}")
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# We store the SETTINGS here, we do not connect yet
DB_SETTINGS = {
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "host": os.getenv("host"),
    "port": os.getenv("port"),
    "database": os.getenv("dbname") # psycopg2 uses 'database', not 'dbname' in kwargs
}

SECRET_KEY = os.getenv("SECRET_KEY")