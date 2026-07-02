"""
Database layer for the Voice-Based Email System.
Uses plain SQLite (no ORM) so the whole thing runs with zero extra services.
"""

import sqlite3
import os
from datetime import datetime
from config import Config


def get_db():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            voice_password_hash TEXT NOT NULL,
            mail_login_email TEXT,
            mail_app_password_encrypted TEXT,
            dark_mode INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email_attempted TEXT,
            success INTEGER NOT NULL,
            method TEXT NOT NULL,
            ip_address TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipient TEXT,
            subject TEXT,
            body TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def log_activity(user_id, action, details=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO activity_logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, action, details, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def log_login_attempt(user_id, email_attempted, success, method, ip_address):
    conn = get_db()
    conn.execute(
        """INSERT INTO login_history (user_id, email_attempted, success, method, ip_address, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, email_attempted, int(success), method, ip_address, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def recent_failed_attempts(email, since_iso):
    conn = get_db()
    row = conn.execute(
        """SELECT COUNT(*) as c FROM login_history
           WHERE email_attempted = ? AND success = 0 AND timestamp > ?""",
        (email, since_iso),
    ).fetchone()
    conn.close()
    return row["c"] if row else 0
