"""
Database initialisation and seed data
======================================
Uses plain sqlite3 (no ORM) so every query is visible and easy to explain.
Call init_db() once at app startup; it is idempotent (uses IF NOT EXISTS).
"""
import sqlite3
import os
from datetime import datetime

# DB file lives at the project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "campus_network.db")


def get_db():
    """Return a new sqlite3 connection with row_factory set to Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables and seed reference data (idempotent)."""
    conn = get_db()
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # TABLE: zones
    # ------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zones (
            code             TEXT PRIMARY KEY,
            name             TEXT NOT NULL,
            primary_admin_id INTEGER
        )
    """)

    # ------------------------------------------------------------------
    # TABLE: admins
    # ------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            zone_code    TEXT    NOT NULL,
            is_backup    INTEGER NOT NULL DEFAULT 0,   -- 0=primary, 1=backup
            availability TEXT    NOT NULL DEFAULT 'Available'
                              CHECK(availability IN ('Available','Busy'))
        )
    """)

    # ------------------------------------------------------------------
    # TABLE: users
    # ------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            usn_or_faculty_id TEXT NOT NULL UNIQUE,
            role             TEXT NOT NULL DEFAULT 'Student'
                                 CHECK(role IN ('Student','Faculty'))
        )
    """)

    # ------------------------------------------------------------------
    # TABLE: complaints
    # ------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            complaint_id      TEXT    PRIMARY KEY,
            user_id           INTEGER NOT NULL REFERENCES users(id),
            location_identifier TEXT  NOT NULL,
            device_type       TEXT    NOT NULL,
            zone_code         TEXT    NOT NULL,
            floor             TEXT    NOT NULL,
            description       TEXT    NOT NULL,
            category          TEXT    NOT NULL,
            priority          TEXT    NOT NULL
                                   CHECK(priority IN ('High','Medium','Low')),
            status            TEXT    NOT NULL DEFAULT 'Pending'
                                   CHECK(status IN ('Pending','Assigned','In Progress','Resolved')),
            assigned_admin_id INTEGER REFERENCES admins(id),
            created_at        TEXT    NOT NULL,
            updated_at        TEXT    NOT NULL
        )
    """)

    conn.commit()

    # ------------------------------------------------------------------
    # SEED data (only if tables are empty)
    # ------------------------------------------------------------------
    if cur.execute("SELECT COUNT(*) FROM admins").fetchone()[0] == 0:
        _seed(cur)
        conn.commit()

    conn.close()


def _seed(cur):
    """Insert seed zones and admins."""

    # --- Seed admins first (without zone FK so we can get IDs) ----------
    admin_rows = [
        # (name, zone_code, is_backup)
        ("Ravi Kumar",     "HOSTEL",  0),
        ("Priya Sharma",   "HOSTEL",  1),
        ("Arjun Nair",     "LAB",     0),
        ("Meena Pillai",   "LAB",     1),
        ("Suresh Babu",    "ADMIN",   0),
        ("Deepa Menon",    "ADMIN",   1),
        ("Kiran Reddy",    "LIB",     0),
        ("Anjali Rao",     "LIB",     1),
        ("Farhan Shaikh",  "CANTEEN", 0),
        ("Lakshmi Iyer",   "CANTEEN", 1),
        ("Nikhil Verma",   "SPORTS",  0),
        ("Sonal Joshi",    "SPORTS",  1),
        # Central admin handles unknown zones and overflow
        ("Central Admin",  "CENTRAL", 0),
    ]

    cur.executemany(
        "INSERT INTO admins (name, zone_code, is_backup, availability) VALUES (?,?,?,'Available')",
        admin_rows
    )

    # Retrieve IDs (SQLite auto-increments from 1)
    admins = cur.execute("SELECT id, name, zone_code, is_backup FROM admins").fetchall()

    # Build a quick lookup: zone -> primary admin id
    primary_map = {}
    for a in admins:
        if a["is_backup"] == 0:
            primary_map[a["zone_code"]] = a["id"]

    # --- Seed zones -------------------------------------------------------
    zone_rows = [
        ("HOSTEL",  "Hostels",        primary_map.get("HOSTEL")),
        ("LAB",     "Laboratories",   primary_map.get("LAB")),
        ("ADMIN",   "Admin Block",    primary_map.get("ADMIN")),
        ("LIB",     "Library",        primary_map.get("LIB")),
        ("CANTEEN", "Canteen",        primary_map.get("CANTEEN")),
        ("SPORTS",  "Sports Complex", primary_map.get("SPORTS")),
        ("CENTRAL", "Central (Unknown Zone)", primary_map.get("CENTRAL")),
    ]

    cur.executemany(
        "INSERT OR IGNORE INTO zones (code, name, primary_admin_id) VALUES (?,?,?)",
        zone_rows
    )


# ------------------------------------------------------------------
# Helper: generate next complaint ID for today
# ------------------------------------------------------------------
def next_complaint_id(conn) -> str:
    """Generate the next CMP-YYYYMMDD-NNNN for today."""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"CMP-{today}-"
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM complaints WHERE complaint_id LIKE ?",
        (prefix + "%",)
    ).fetchone()
    seq = (row["cnt"] if row else 0) + 1
    return f"{prefix}{seq:04d}"
