"""
app.py – Campus Network Fault Reporter
========================================
Single entry-point for the Flask application.
Run:  python app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))   # ensure local packages resolve

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, session
)
from datetime import datetime

from models.db import init_db, get_db
from services.validation_service import validate_identifier, quick_validate
from services.classifier import classify_complaint
from services.routing import ZONE_NAMES, ROUTING_TABLE
from services.routing_service import (
    submit_complaint,
    toggle_admin_availability,
    update_complaint_status,
    get_all_zones_with_admins,
    get_waiting_queue,
    get_analytics,
)
from services.dfa_validator import dfa_validate, get_dfa_description

app = Flask(__name__)
app.secret_key = "campus-net-secret-2026"   # for flash messages

# Add enumerate as a Jinja2 filter so templates can use {{ list | enumerate }}
app.jinja_env.filters['enumerate'] = enumerate

# ---------------------------------------------------------------------------
# App startup – initialise DB
# ---------------------------------------------------------------------------
with app.app_context():
    init_db()


# ===========================================================================
# UTILITY
# ===========================================================================

def _row_to_dict(row):
    """sqlite3.Row -> plain dict."""
    return dict(row) if row else None


# ===========================================================================
# PAGE ROUTES
# ===========================================================================

@app.route("/")
def home():
    """Landing / home page."""
    conn = get_db()
    overall = conn.execute("""
        SELECT
          COUNT(*) as total,
          SUM(CASE WHEN status='Pending'    THEN 1 ELSE 0 END) as pending,
          SUM(CASE WHEN status='Resolved'   THEN 1 ELSE 0 END) as resolved,
          SUM(CASE WHEN status='Assigned'   THEN 1 ELSE 0 END) as assigned
        FROM complaints
    """).fetchone()
    conn.close()
    return render_template("index.html", stats=dict(overall) if overall else {})


# ------------------------------------------------------------------
# Registration & Complaint Submission
# ------------------------------------------------------------------
@app.route("/submit", methods=["GET", "POST"])
def submit():
    """Complaint submission form."""
    if request.method == "GET":
        return render_template("submit.html",
                               device_types=["WIFI", "LAN"],
                               location_codes=list(ROUTING_TABLE.keys()))

    # POST – process form
    data = request.form
    result = submit_complaint(
        name=data.get("name", "").strip(),
        usn_or_faculty_id=data.get("usn_or_faculty_id", "").strip(),
        role=data.get("role", "Student"),
        device_type=data.get("device_type", "").strip(),
        location_code=data.get("location_code", "").strip(),
        floor=data.get("floor", "").strip(),
        description=data.get("description", "").strip(),
    )
    if result["success"]:
        return render_template("submit.html",
                               device_types=["WIFI", "LAN"],
                               location_codes=list(ROUTING_TABLE.keys()),
                               result=result)
    else:
        return render_template("submit.html",
                               device_types=["WIFI", "LAN"],
                               location_codes=list(ROUTING_TABLE.keys()),
                               error=result.get("error"),
                               validation=result.get("validation"))


# ------------------------------------------------------------------
# User Dashboard
# ------------------------------------------------------------------
@app.route("/dashboard")
def user_dashboard():
    """User dashboard – summary counts + complaint tracking."""
    conn = get_db()

    # Summary stats across all complaints
    stats = conn.execute("""
        SELECT
          COUNT(*) as total,
          SUM(CASE WHEN status='Pending'     THEN 1 ELSE 0 END) as pending,
          SUM(CASE WHEN status='Assigned'    THEN 1 ELSE 0 END) as assigned,
          SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) as in_progress,
          SUM(CASE WHEN status='Resolved'    THEN 1 ELSE 0 END) as resolved
        FROM complaints
    """).fetchone()

    # Optional: filter by complaint ID
    track_id  = request.args.get("complaint_id", "").strip()
    tracked   = None
    track_err = None

    if track_id:
        row = conn.execute("""
            SELECT c.*, u.name as user_name, u.usn_or_faculty_id,
                   a.name as admin_name, a.zone_code as admin_zone
            FROM complaints c
            JOIN users u ON u.id = c.user_id
            LEFT JOIN admins a ON a.id = c.assigned_admin_id
            WHERE c.complaint_id = ?
        """, (track_id.upper(),)).fetchone()
        if row:
            tracked = _row_to_dict(row)
        else:
            track_err = f"No complaint found with ID '{track_id}'"

    # Recent complaints list (last 20)
    recent = conn.execute("""
        SELECT c.*, u.name as user_name, a.name as admin_name
        FROM complaints c
        JOIN users u ON u.id = c.user_id
        LEFT JOIN admins a ON a.id = c.assigned_admin_id
        ORDER BY c.created_at DESC LIMIT 20
    """).fetchall()
    conn.close()

    return render_template("user_dashboard.html",
                           stats=dict(stats) if stats else {},
                           tracked=tracked,
                           track_id=track_id,
                           track_err=track_err,
                           recent=[_row_to_dict(r) for r in recent])


# ------------------------------------------------------------------
# Admin Dashboard
# ------------------------------------------------------------------
@app.route("/admin-dashboard")
def admin_dashboard():
    """Network administrator dashboard."""
    conn = get_db()
    admins = conn.execute(
        "SELECT * FROM admins ORDER BY zone_code, is_backup"
    ).fetchall()

    selected_id = request.args.get("admin_id", type=int)
    complaints  = []
    selected_admin = None

    if selected_id:
        selected_admin = _row_to_dict(
            conn.execute("SELECT * FROM admins WHERE id=?", (selected_id,)).fetchone()
        )
        complaints = conn.execute("""
            SELECT c.*, u.name as user_name, u.usn_or_faculty_id
            FROM complaints c
            JOIN users u ON u.id = c.user_id
            WHERE c.assigned_admin_id = ?
            ORDER BY
              CASE c.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
              c.created_at DESC
        """, (selected_id,)).fetchall()
        complaints = [_row_to_dict(r) for r in complaints]

    conn.close()
    return render_template("admin_dashboard.html",
                           admins=[_row_to_dict(a) for a in admins],
                           selected_admin=selected_admin,
                           selected_id=selected_id,
                           complaints=complaints)


# ------------------------------------------------------------------
# Routing Management Dashboard
# ------------------------------------------------------------------
@app.route("/routing")
def routing_dashboard():
    """Routing management – zones, admins, queue."""
    conn = get_db()
    zones_data = get_all_zones_with_admins(conn)
    queue      = get_waiting_queue(conn)
    conn.close()
    return render_template("routing_dashboard.html",
                           zones_data=zones_data,
                           queue=queue,
                           zone_names=ZONE_NAMES)


# ------------------------------------------------------------------
# Analytics Dashboard
# ------------------------------------------------------------------
@app.route("/analytics")
def analytics_dashboard():
    """Analytics dashboard with Chart.js charts."""
    conn = get_db()
    data = get_analytics(conn)
    conn.close()
    return render_template("analytics.html", analytics=data, zone_names=ZONE_NAMES)


# ------------------------------------------------------------------
# DFA Simulator
# ------------------------------------------------------------------
@app.route("/dfa-simulator")
def dfa_simulator():
    """DFA simulator – step-by-step state transitions."""
    identifier = request.args.get("identifier", "").strip().upper()
    sim_result = None
    if identifier:
        sim_result = quick_validate(identifier)
    return render_template("dfa_simulator.html",
                           identifier=identifier,
                           sim_result=sim_result,
                           dfa_desc=get_dfa_description())


# ===========================================================================
# JSON / AJAX API ROUTES
# ===========================================================================

@app.route("/api/validate", methods=["POST"])
def api_validate():
    """
    Live identifier validation (called by JS as user fills the form).
    Body: { device_type, location_code, floor }
    """
    data        = request.get_json(force=True) or {}
    device_type = data.get("device_type", "").strip().upper()
    loc_code    = data.get("location_code", "").strip().upper()
    floor       = data.get("floor", "").strip()

    if not device_type or not loc_code or not floor:
        return jsonify({"is_valid": False, "identifier": "", "message": "Incomplete fields"})

    result = validate_identifier(device_type, loc_code, floor)
    return jsonify({
        "identifier":   result["identifier"],
        "is_valid":     result["is_valid"],
        "both_agree":   result["both_agree"],
        "message":      result["message"],
        "dfa_valid":    result["dfa_result"]["valid"],
        "regex_valid":  result["regex_result"]["valid"],
    })


@app.route("/api/classify", methods=["POST"])
def api_classify():
    """
    Live complaint classification (called as user types description).
    Body: { description }
    """
    data        = request.get_json(force=True) or {}
    description = data.get("description", "")
    result      = classify_complaint(description)
    return jsonify(result)


@app.route("/api/admin/toggle", methods=["POST"])
def api_toggle_admin():
    """
    Toggle admin availability (AJAX).
    Body: { admin_id, availability }
    """
    data         = request.get_json(force=True) or {}
    admin_id     = data.get("admin_id")
    availability = data.get("availability")

    if admin_id is None or availability not in ("Available", "Busy"):
        return jsonify({"success": False, "error": "Invalid parameters"}), 400

    result = toggle_admin_availability(int(admin_id), availability)
    return jsonify(result)


@app.route("/api/complaint/status", methods=["POST"])
def api_update_status():
    """
    Update complaint status (AJAX).
    Body: { complaint_id, status, admin_id }
    """
    data         = request.get_json(force=True) or {}
    complaint_id = data.get("complaint_id", "").strip()
    new_status   = data.get("status", "").strip()
    admin_id     = data.get("admin_id")

    valid_statuses = {"Pending", "Assigned", "In Progress", "Resolved"}
    if not complaint_id or new_status not in valid_statuses or admin_id is None:
        return jsonify({"success": False, "error": "Invalid parameters"}), 400

    result = update_complaint_status(complaint_id, new_status, int(admin_id))
    return jsonify(result)


@app.route("/api/dfa/simulate", methods=["POST"])
def api_dfa_simulate():
    """
    Full DFA simulation with step-by-step path.
    Body: { identifier }
    """
    data       = request.get_json(force=True) or {}
    identifier = data.get("identifier", "").strip().upper()
    if not identifier:
        return jsonify({"error": "No identifier provided"}), 400

    result = quick_validate(identifier)
    return jsonify(result)


@app.route("/api/complaints", methods=["GET"])
def api_complaints():
    """
    Return filtered list of complaints as JSON.
    Query params: status, zone_code, priority, admin_id
    """
    conn    = get_db()
    clauses = []
    params  = []

    for field in ("status", "zone_code", "priority"):
        val = request.args.get(field)
        if val:
            clauses.append(f"c.{field}=?")
            params.append(val)

    admin_id = request.args.get("admin_id", type=int)
    if admin_id:
        clauses.append("c.assigned_admin_id=?")
        params.append(admin_id)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    rows = conn.execute(f"""
        SELECT c.*, u.name as user_name, a.name as admin_name
        FROM complaints c
        JOIN users u ON u.id = c.user_id
        LEFT JOIN admins a ON a.id = c.assigned_admin_id
        {where}
        ORDER BY
          CASE c.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
          c.created_at DESC
    """, params).fetchall()
    conn.close()
    return jsonify([_row_to_dict(r) for r in rows])


@app.route("/api/stats")
def api_stats():
    """Quick stat counts for animated cards."""
    conn = get_db()
    row = conn.execute("""
        SELECT
          COUNT(*) as total,
          SUM(CASE WHEN status='Pending'     THEN 1 ELSE 0 END) as pending,
          SUM(CASE WHEN status='Assigned'    THEN 1 ELSE 0 END) as assigned,
          SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) as in_progress,
          SUM(CASE WHEN status='Resolved'    THEN 1 ELSE 0 END) as resolved
        FROM complaints
    """).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)
