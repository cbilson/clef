import mysql.connector
import os

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
if not DB_USER or not DB_PASSWORD or not DB_NAME or not DB_HOST :
    raise Exception("Database environment variables not found.")

def connect():
    return mysql.connector.connect(user=DB_USER, password=DB_PASSWORD,
                                   host=DB_HOST, database=DB_NAME)

# wip: this isn't working yet
def do(action, db=None):
    cleanup_database_connection = False
    if not db:
        db = db.connect()
        cleanup_database_connection = True

    try:
        cursor = db.cursor()
        res = action(cursor)
        db.commit()
        return res
    finally:
        if cleanup_database_connection:
            db.close()
