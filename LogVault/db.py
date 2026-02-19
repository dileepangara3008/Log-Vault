import psycopg2
from config import DB_SETTINGS

def get_db_connection():
    conn = psycopg2.connect(**DB_SETTINGS)
    return conn
