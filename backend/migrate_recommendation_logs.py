"""
One-off migration: 
1. Ensures `rainfall_growing_season` EXISTS.
2. Ensures `fertilizer_crop_type` is DROPPED.

Reuses the SAME .env variables as app.py (MYSQLUSER, MYSQLPASSWORD,
MYSQLHOST, MYSQLPORT, MYSQLDATABASE) — run this from the same folder as
your .env file.

Safe to run more than once: it checks information_schema first and only
adds/drops a column if necessary.

Usage:
    pip install mysql-connector-python python-dotenv --break-system-packages
    python migrate_recommendation_logs.py
"""

import os
import sys

import mysql.connector
from dotenv import load_dotenv

load_dotenv()  # reads .env from the current working directory

DB_CONFIG = {
    "user": os.getenv("MYSQLUSER"),
    "password": os.getenv("MYSQLPASSWORD"),
    "host": os.getenv("MYSQLHOST"),
    "port": os.getenv("MYSQLPORT"),
    "database": os.getenv("MYSQLDATABASE"),
}

MIGRATIONS = [
    {
        "action": "add",
        "column": "rainfall_growing_season",
        "ddl": "ALTER TABLE recommendation_logs ADD COLUMN rainfall_growing_season FLOAT NULL AFTER rainfall",
    },
    {
        "action": "drop",
        "column": "fertilizer_crop_type",
        "ddl": "ALTER TABLE recommendation_logs DROP COLUMN fertilizer_crop_type",
    },
]


def main():
    missing = [k for k, v in DB_CONFIG.items() if not v]
    if missing:
        print(f"[Error] Missing env vars: {missing}. Is your .env in this folder?")
        sys.exit(1)

    print(f"Connecting to {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']} ...")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
    except Exception as e:
        print(f"[Error] Failed to connect to database: {e}")
        sys.exit(1)

    for m in MIGRATIONS:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'recommendation_logs' AND COLUMN_NAME = %s
            """,
            (DB_CONFIG["database"], m["column"]),
        )
        exists = cursor.fetchone()[0] > 0

        if m["action"] == "add":
            if exists:
                print(f"[Skip] '{m['column']}' already exists.")
            else:
                print(f"[Adding] {m['column']} ...")
                cursor.execute(m["ddl"])
                conn.commit()
                print(f"[Done] '{m['column']}' added.")
                
        elif m["action"] == "drop":
            if not exists:
                print(f"[Skip] '{m['column']}' is already dropped (does not exist).")
            else:
                print(f"[Dropping] {m['column']} ...")
                cursor.execute(m["ddl"])
                conn.commit()
                print(f"[Done] '{m['column']}' dropped.")

    cursor.close()
    conn.close()
    print("Migration complete. The database schema is now up to date.")


if __name__ == "__main__":
    main()