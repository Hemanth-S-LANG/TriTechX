"""
demo_workflow.py – Full End-to-End Demonstration
=================================================
Runs the complete workflow without the web UI:
  1. Register a user
  2. Validate location identifier (DFA + Regex)
  3. Classify complaint
  4. Route to admin
  5. Update status to Assigned → In Progress → Resolved
  6. Show final complaint record

Run:  python demo_workflow.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import textwrap
from datetime import datetime

# Colour helpers for terminal output (Windows-safe)
try:
    import colorama
    colorama.init()
    GREEN  = "\033[92m"
    CYAN   = "\033[96m"
    YELLOW = "\033[93m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
except ImportError:
    GREEN = CYAN = YELLOW = BOLD = RESET = ""


def banner(text):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

def step(n, text):
    print(f"\n{BOLD}{YELLOW}[ Step {n} ]{RESET} {text}")

def ok(text):
    print(f"  {GREEN}✔{RESET}  {text}")

def info(text):
    print(f"       {text}")


banner("Campus Network Fault Reporter – Full Demo Workflow")

# -------------------------------------------------------------------------
# STEP 1: Initialise database
# -------------------------------------------------------------------------
step(1, "Initialise SQLite database")
from models.db import init_db, get_db
init_db()
ok("Database initialised (tables created, seed data loaded).")

# -------------------------------------------------------------------------
# STEP 2: Validate location identifier – DFA and Regex
# -------------------------------------------------------------------------
step(2, "Validate location identifier with DFA and Regex")

from services.validation_service import quick_validate

test_cases = [
    ("WIFI-LIB-2",   True,  "valid"),
    ("LAN-HOST-0",   True,  "valid"),
    ("WLAN-LAB-3",   False, "invalid device type"),
    ("WIFI-XYZ-5",   False, "invalid location code"),
    ("LAN-LAB-10",   False, "floor out of range"),
]

for ident, expected, note in test_cases:
    r = quick_validate(ident)
    icon = GREEN + "✔" + RESET if r["is_valid"] == expected else "✘"
    agreement = "agree" if r["both_agree"] else "DISAGREE"
    print(f"  {icon}  {ident:<18}  DFA={'Valid' if r['dfa_result']['valid'] else 'Invalid':8}  "
          f"Regex={'Valid' if r['regex_result']['valid'] else 'Invalid':8}  "
          f"[{agreement}]  ({note})")

# -------------------------------------------------------------------------
# STEP 3: Classify complaint description
# -------------------------------------------------------------------------
step(3, "Classify complaint descriptions")

from services.classifier import classify_complaint

descriptions = [
    ("Cannot connect to wifi, intermittent disconnections", "Connectivity"),
    ("Ethernet cable is physically damaged and router is broken", "Hardware"),
    ("IP address and DNS settings are misconfigured, wrong subnet", "Configuration"),
    ("Unauthorized access attempt, possible intrusion attack", "Security"),
    ("Something seems off with the network", "Unknown"),
    ("Unauthorized access and slow connectivity", "Security"),  # multi-keyword
]

for desc, expected in descriptions:
    r = classify_complaint(desc)
    icon = GREEN + "✔" + RESET if r["category"] == expected else "~"
    kw = ", ".join(r["matched_keywords"][:3])
    print(f"  {icon}  [{r['category']:15}] [{r['priority']:6}]  Keywords: {kw or 'none'}")
    info(f'"{desc[:60]}…"' if len(desc) > 60 else f'"{desc}"')

# -------------------------------------------------------------------------
# STEP 4: Route complaint via submit_complaint()
# -------------------------------------------------------------------------
step(4, "Submit and route a complaint through the full pipeline")

from services.routing_service import submit_complaint

result = submit_complaint(
    name             = "Riya Sharma",
    usn_or_faculty_id= "1AM22CS042",
    role             = "Student",
    device_type      = "WIFI",
    location_code    = "LIB",
    floor            = "2",
    description      = "WiFi connection is intermittent and very slow in the library building",
)

if result["success"]:
    ok(f"Complaint submitted: {BOLD}{result['complaint_id']}{RESET}")
    info(f"Identifier  : {result['identifier']}")
    info(f"Category    : {result['category']}  |  Priority: {result['priority']}")
    info(f"Zone        : {result['zone_name']}")
    info(f"Status      : {result['status']}")
    info(f"Admin       : {result['assigned_admin'] or 'Waiting in queue'}")
    info(f"Note        : {result['routing_note']}")
    complaint_id = result["complaint_id"]
    admin_id     = result["assigned_admin_id"]
else:
    print(f"  ✘  Failed: {result['error']}")
    sys.exit(1)

# -------------------------------------------------------------------------
# STEP 5: Simulate admin-busy → backup routing
# -------------------------------------------------------------------------
step(5, "Demonstrate backup routing (mark primary admin busy, then submit)")

conn = get_db()
zone = conn.execute("SELECT primary_admin_id FROM zones WHERE code='LAB'").fetchone()
primary_id = zone["primary_admin_id"]
conn.execute("UPDATE admins SET availability='Busy' WHERE id=?", (primary_id,))
conn.commit()
conn.close()

result2 = submit_complaint(
    name="Arjun Nair", usn_or_faculty_id="1AM22CS099", role="Student",
    device_type="LAN", location_code="LAB", floor="3",
    description="Ethernet cable is completely broken, router port damaged",
)

if result2["success"]:
    ok(f"Complaint {result2['complaint_id']} → {result2['status']}")
    info(f"Admin: {result2['assigned_admin'] or 'queued'} | Note: {result2['routing_note']}")
else:
    info(f"Failed: {result2['error']}")

# -------------------------------------------------------------------------
# STEP 6: Demonstrate priority queue (all admins busy)
# -------------------------------------------------------------------------
step(6, "Demonstrate priority queue (all admins busy)")

conn = get_db()
conn.execute("UPDATE admins SET availability='Busy'")
conn.commit()
conn.close()

queue_submissions = [
    ("1AM22CS011", "LAN",  "LAB", "1", "IP address misconfigured subnet wrong"),    # Low
    ("1AM22CS022", "WIFI", "LIB", "2", "intermittent slow connection dropped"),      # Medium
    ("1AM22CS033", "LAN",  "HOST","0", "unauthorized access attack intrusion detected"), # High
]

for usn, dt, lc, fl, desc in queue_submissions:
    r = submit_complaint(f"User-{usn}", usn, "Student", dt, lc, fl, desc)
    clf = r.get("classification", {})
    ok(f"{r['complaint_id']} → queued  Priority: {r['priority']:6}  Category: {r['category']}")

from services.routing_service import get_waiting_queue
conn = get_db()
queue = get_waiting_queue(conn)
conn.close()

print(f"\n  Priority queue order ({len(queue)} items):")
for i, c in enumerate(queue, 1):
    print(f"    {i}. [{c['priority']:6}] {c['complaint_id']}  –  {c['category']}")

# -------------------------------------------------------------------------
# STEP 7: Status progression  Assigned → In Progress → Resolved
# -------------------------------------------------------------------------
step(7, "Update complaint status: Assigned → In Progress → Resolved")

from services.routing_service import update_complaint_status

# Use the first complaint which should be assigned
if admin_id:
    statuses = ["In Progress", "Resolved"]
    for new_status in statuses:
        upd = update_complaint_status(complaint_id, new_status, admin_id)
        icon = GREEN + "✔" + RESET if upd["success"] else "✘"
        print(f"  {icon}  {complaint_id} → {new_status}")
        if upd.get("auto_assigned"):
            ok(f"Auto-assigned next queued complaint: {upd['auto_assigned']['complaint_id']}")

# -------------------------------------------------------------------------
# STEP 8: Final record
# -------------------------------------------------------------------------
step(8, "Final complaint record from database")

conn = get_db()
row = conn.execute("""
    SELECT c.*, u.name as user_name, a.name as admin_name
    FROM complaints c
    JOIN users u ON u.id = c.user_id
    LEFT JOIN admins a ON a.id = c.assigned_admin_id
    WHERE c.complaint_id=?
""", (complaint_id,)).fetchone()
conn.close()

if row:
    ok("Final record:")
    for col in row.keys():
        val = row[col]
        if val is not None:
            print(f"    {col:<25} : {val}")

# -------------------------------------------------------------------------
banner("Demo Complete – All steps executed successfully!")
print()
