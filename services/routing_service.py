"""
Routing Service
================
Wraps the pure routing logic (Part B) with SQLite access.

Flow:
  1. Validate identifier (already done before calling here).
  2. Extract zone from identifier.
  3. Find primary admin for that zone.
  4. If primary is Available  -> assign to primary.
  5. If primary is Busy       -> try backup admins for the zone (first Available).
  6. If all admins Busy       -> place in waiting queue (priority-based).
  7. When an admin becomes Available, auto-assign the top-priority waiting complaint.

The 'waiting queue' is simply complaints with status='Pending' and
assigned_admin_id=NULL, ordered by PRIORITY_WEIGHT then created_at when
fetching next to assign.
"""
import heapq
from datetime import datetime

from services.routing import (
    get_zone_for_identifier,
    PRIORITY_WEIGHT,
    ZONE_NAMES,
)
from services.classifier import classify_complaint
from services.validation_service import validate_identifier
from models.db import get_db, next_complaint_id


# ---------------------------------------------------------------------------
# Main submission entry point
# ---------------------------------------------------------------------------

def submit_complaint(
    name: str,
    usn_or_faculty_id: str,
    role: str,
    device_type: str,
    location_code: str,
    floor: str,
    description: str,
) -> dict:
    """
    Full pipeline: validate -> classify -> route -> persist -> assign.
    Returns a result dict with all details needed by the UI.
    """
    # 1. Validate identifier
    val = validate_identifier(device_type, location_code, floor)
    if not val["is_valid"]:
        return {
            "success":    False,
            "error":      val["message"],
            "validation": val,
        }

    identifier = val["identifier"]

    # 2. Classify complaint
    clf = classify_complaint(description)
    category = clf["category"]
    priority = clf["priority"]

    # 3. Determine zone
    zone_info = get_zone_for_identifier(identifier)
    zone_code = zone_info["zone_code"] or "CENTRAL"

    conn = get_db()
    try:
        # 4. Upsert user (insert if not exists, return id)
        user_id = _upsert_user(conn, name, usn_or_faculty_id, role)

        # 5. Generate unique complaint ID
        complaint_id = next_complaint_id(conn)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 6. Find an available admin
        assigned_admin_id, routing_note = _find_admin(conn, zone_code, priority)

        status = "Assigned" if assigned_admin_id else "Pending"

        # 7. Persist complaint
        conn.execute("""
            INSERT INTO complaints
              (complaint_id, user_id, location_identifier, device_type, zone_code,
               floor, description, category, priority, status, assigned_admin_id,
               created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            complaint_id, user_id, identifier, device_type.upper(), zone_code,
            floor, description, category, priority, status, assigned_admin_id,
            now, now,
        ))

        # 8. Mark assigned admin as Busy
        if assigned_admin_id:
            conn.execute(
                "UPDATE admins SET availability='Busy' WHERE id=?",
                (assigned_admin_id,)
            )

        conn.commit()

        # Fetch admin name for response
        admin_name = None
        if assigned_admin_id:
            row = conn.execute(
                "SELECT name FROM admins WHERE id=?", (assigned_admin_id,)
            ).fetchone()
            if row:
                admin_name = row["name"]

        return {
            "success":          True,
            "complaint_id":     complaint_id,
            "identifier":       identifier,
            "category":         category,
            "priority":         priority,
            "zone_code":        zone_code,
            "zone_name":        ZONE_NAMES.get(zone_code, zone_code),
            "status":           status,
            "assigned_admin_id": assigned_admin_id,
            "assigned_admin":   admin_name,
            "routing_note":     routing_note,
            "validation":       val,
            "classification":   clf,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Admin availability toggle + auto-assign from queue
# ---------------------------------------------------------------------------

def toggle_admin_availability(admin_id: int, new_availability: str) -> dict:
    """
    Set admin availability. If switching to 'Available', auto-assign the
    highest-priority waiting complaint in that admin's zone (or any zone if
    central admin).
    Returns updated admin info and optionally the auto-assigned complaint.
    """
    conn = get_db()
    try:
        conn.execute(
            "UPDATE admins SET availability=? WHERE id=?",
            (new_availability, admin_id)
        )
        conn.commit()

        auto_assigned = None
        if new_availability == "Available":
            auto_assigned = _auto_assign_from_queue(conn, admin_id)
            if auto_assigned:
                conn.commit()

        admin = conn.execute(
            "SELECT * FROM admins WHERE id=?", (admin_id,)
        ).fetchone()

        return {
            "success":      True,
            "admin":        dict(admin),
            "auto_assigned": auto_assigned,
        }
    finally:
        conn.close()


def update_complaint_status(complaint_id: str, new_status: str, admin_id: int) -> dict:
    """
    Update complaint status. When set to 'Resolved', free the admin
    and auto-assign next waiting complaint.
    """
    conn = get_db()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE complaints SET status=?, updated_at=? WHERE complaint_id=?",
            (new_status, now, complaint_id)
        )
        conn.commit()

        auto_assigned = None
        if new_status == "Resolved":
            # Free this admin
            conn.execute(
                "UPDATE admins SET availability='Available' WHERE id=?",
                (admin_id,)
            )
            conn.commit()
            auto_assigned = _auto_assign_from_queue(conn, admin_id)
            if auto_assigned:
                conn.commit()

        return {"success": True, "auto_assigned": auto_assigned}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _upsert_user(conn, name: str, usn_or_faculty_id: str, role: str) -> int:
    """Insert user if not exists, return their id."""
    row = conn.execute(
        "SELECT id FROM users WHERE usn_or_faculty_id=?", (usn_or_faculty_id,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO users (name, usn_or_faculty_id, role) VALUES (?,?,?)",
        (name, usn_or_faculty_id, role)
    )
    return cur.lastrowid


def _find_admin(conn, zone_code: str, priority: str):
    """
    Try to find an Available admin for zone_code.
    Returns (admin_id | None, routing_note string).
    """
    # Fetch zone's primary admin
    zone_row = conn.execute(
        "SELECT primary_admin_id FROM zones WHERE code=?", (zone_code,)
    ).fetchone()

    if zone_row and zone_row["primary_admin_id"]:
        primary_id = zone_row["primary_admin_id"]
        primary = conn.execute(
            "SELECT id, name, availability FROM admins WHERE id=?", (primary_id,)
        ).fetchone()

        if primary and primary["availability"] == "Available":
            return primary["id"], f"Assigned to primary admin {primary['name']}"

        # Primary busy — try backup admins for this zone
        backups = conn.execute(
            "SELECT id, name, availability FROM admins "
            "WHERE zone_code=? AND is_backup=1 ORDER BY id",
            (zone_code,)
        ).fetchall()

        for b in backups:
            if b["availability"] == "Available":
                return b["id"], f"Primary busy — assigned to backup admin {b['name']}"

        # All zone admins busy — try central admin
        central = conn.execute(
            "SELECT id, name, availability FROM admins "
            "WHERE zone_code='CENTRAL' ORDER BY id LIMIT 1"
        ).fetchone()

        if central and central["availability"] == "Available":
            return central["id"], (
                f"All zone admins busy — escalated to central admin {central['name']}"
            )

    # No available admin at all -> waiting queue
    return None, "All admins busy — complaint placed in priority-based waiting queue"


def _auto_assign_from_queue(conn, admin_id: int):
    """
    Find the highest-priority waiting complaint and assign it to admin_id.
    Priority order: High(1) > Medium(2) > Low(3), then earliest created_at.
    Returns complaint dict or None.
    """
    admin = conn.execute(
        "SELECT zone_code, is_backup FROM admins WHERE id=?", (admin_id,)
    ).fetchone()
    if not admin:
        return None

    # Build priority CASE expression for ordering
    priority_case = "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END"

    # Central or backup admins can pick up any zone's queue
    if admin["zone_code"] == "CENTRAL" or admin["is_backup"]:
        waiting = conn.execute(f"""
            SELECT * FROM complaints
            WHERE status='Pending' AND assigned_admin_id IS NULL
            ORDER BY {priority_case}, created_at
            LIMIT 1
        """).fetchone()
    else:
        # Find zone for this admin
        zone_row = conn.execute(
            "SELECT code FROM zones WHERE primary_admin_id=?", (admin_id,)
        ).fetchone()
        zone_code = zone_row["code"] if zone_row else None

        if not zone_code:
            return None

        waiting = conn.execute(f"""
            SELECT * FROM complaints
            WHERE status='Pending' AND assigned_admin_id IS NULL
              AND zone_code=?
            ORDER BY {priority_case}, created_at
            LIMIT 1
        """, (zone_code,)).fetchone()

    if not waiting:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE complaints
        SET assigned_admin_id=?, status='Assigned', updated_at=?
        WHERE complaint_id=?
    """, (admin_id, now, waiting["complaint_id"]))
    conn.execute(
        "UPDATE admins SET availability='Busy' WHERE id=?", (admin_id,)
    )

    return dict(waiting)


# ---------------------------------------------------------------------------
# Query helpers used by Flask routes
# ---------------------------------------------------------------------------

def get_all_zones_with_admins(conn):
    """Return list of zones each with their admins and complaint counts."""
    zones = conn.execute("SELECT * FROM zones ORDER BY code").fetchall()
    result = []
    for z in zones:
        admins = conn.execute(
            "SELECT * FROM admins WHERE zone_code=? ORDER BY is_backup",
            (z["code"],)
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) as c FROM complaints WHERE zone_code=?",
            (z["code"],)
        ).fetchone()["c"]
        waiting = conn.execute(
            "SELECT COUNT(*) as c FROM complaints "
            "WHERE zone_code=? AND status='Pending' AND assigned_admin_id IS NULL",
            (z["code"],)
        ).fetchone()["c"]
        result.append({
            "zone":    dict(z),
            "admins":  [dict(a) for a in admins],
            "total":   total,
            "waiting": waiting,
        })
    return result


def get_waiting_queue(conn):
    """Return all queued (Pending, unassigned) complaints ordered by priority then time."""
    priority_case = "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END"
    rows = conn.execute(f"""
        SELECT c.*, u.name as user_name, u.usn_or_faculty_id
        FROM complaints c
        JOIN users u ON u.id = c.user_id
        WHERE c.status='Pending' AND c.assigned_admin_id IS NULL
        ORDER BY {priority_case}, c.created_at
    """).fetchall()
    return [dict(r) for r in rows]


def get_analytics(conn) -> dict:
    """Aggregate stats for the analytics dashboard."""
    # Zone-wise totals
    zone_stats = conn.execute("""
        SELECT zone_code, COUNT(*) as total,
               SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END) as resolved
        FROM complaints GROUP BY zone_code
    """).fetchall()

    # Category-wise
    cat_stats = conn.execute("""
        SELECT category, COUNT(*) as total FROM complaints GROUP BY category
    """).fetchall()

    # Overall resolved vs unresolved
    overall = conn.execute("""
        SELECT
          COUNT(*) as total,
          SUM(CASE WHEN status='Resolved'  THEN 1 ELSE 0 END) as resolved,
          SUM(CASE WHEN status!='Resolved' THEN 1 ELSE 0 END) as unresolved,
          SUM(CASE WHEN status='Pending'   THEN 1 ELSE 0 END) as pending,
          SUM(CASE WHEN status='Assigned'  THEN 1 ELSE 0 END) as assigned,
          SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) as in_progress
        FROM complaints
    """).fetchone()

    return {
        "zone_stats":     [dict(r) for r in zone_stats],
        "category_stats": [dict(r) for r in cat_stats],
        "overall":        dict(overall),
    }
