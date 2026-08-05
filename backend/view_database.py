"""
Quick read-only viewer for the AgroSense database — prints the most recent
rows from recommendation_logs and sensor_readings.

Reuses the SAME .env variables as app.py. Run from the same folder as
your .env file.

Usage:
    python view_database.py                # last 10 rows of each table
    python view_database.py --limit 20     # last 20 rows of each table
    python view_database.py --table recommendation_logs
    python view_database.py --table sensor_readings
"""

import argparse
import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("MYSQLUSER"),
    "password": os.getenv("MYSQLPASSWORD"),
    "host": os.getenv("MYSQLHOST"),
    "port": os.getenv("MYSQLPORT"),
    "database": os.getenv("MYSQLDATABASE"),
}


def print_table(cursor, table_name, limit):
    print(f"\n{'=' * 70}\n{table_name}  (most recent {limit})\n{'=' * 70}")

    cursor.execute(f"SELECT COUNT(*) AS n FROM {table_name}")
    total = cursor.fetchone()["n"]
    print(f"Total rows in table: {total}\n")

    cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()

    if not rows:
        print("(no rows yet)")
        return

    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}

    header = " | ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        print(" | ".join(str(r[c]).ljust(widths[c]) for c in cols))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="rows to show per table (default: 10)")
    parser.add_argument(
        "--table",
        choices=["recommendation_logs", "sensor_readings", "all"],
        default="all",
        help="which table to show (default: all)",
    )
    args = parser.parse_args()

    missing = [k for k, v in DB_CONFIG.items() if not v]
    if missing:
        print(f"[Error] Missing env vars: {missing}. Is your .env in this folder?")
        return

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    if args.table in ("recommendation_logs", "all"):
        print_table(cursor, "recommendation_logs", args.limit)
    if args.table in ("sensor_readings", "all"):
        print_table(cursor, "sensor_readings", args.limit)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()