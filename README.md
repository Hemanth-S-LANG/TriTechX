# P1 – Campus Network Fault Reporter and Intelligent Complaint Routing System
**BCS503 (Automata Theory & Computability) + BCS502 (Computer Networks)**

A fully functional, responsive web-based application that demonstrates DFA construction, regex validation, fault classification, network routing, priority-based complaint queuing, and real-time status tracking.

---

## Project Structure

```
TriTechX/
│
├── app.py                      ← Flask application entry point (Part C)
├── demo_workflow.py            ← Full end-to-end CLI demo (Part D)
├── campus_network.db           ← SQLite database (auto-created on first run)
│
├── services/                   ← Parts A & B core logic
│   ├── dfa_validator.py        ← DFA construction + step-by-step simulation
│   ├── regex_validator.py      ← Regex-based identifier validation
│   ├── classifier.py           ← Keyword-based fault classifier
│   ├── routing.py              ← Routing table + zone/identifier logic
│   ├── validation_service.py   ← Wraps DFA + regex with agreement check
│   └── routing_service.py      ← DB-backed routing, assignment, queue logic
│
├── models/
│   └── db.py                   ← SQLite schema, seed data, DB helpers
│
├── templates/                  ← Jinja2 HTML templates (Bootstrap 5)
│   ├── base.html               ← Navbar, footer, dark mode
│   ├── index.html              ← Landing / home page
│   ├── submit.html             ← Complaint submission + live preview
│   ├── user_dashboard.html     ← User stats + complaint tracker
│   ├── admin_dashboard.html    ← Admin complaint management
│   ├── routing_dashboard.html  ← Zone overview + priority queue
│   ├── analytics.html          ← Chart.js analytics dashboard
│   └── dfa_simulator.html      ← DFA step-by-step simulator
│
├── static/
│   ├── css/style.css           ← Custom design system (indigo/teal, no-red)
│   └── js/main.js              ← Count-up, toast, fetch helper, dark mode
│
├── tests/
│   └── test_all.py             ← 26 pytest test cases (Part D)
│
├── TEST_REPORT.md              ← Test case table with pass/fail results
└── README.md                   ← This file
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.11 or newer
- pip

### 2. Install dependencies

```bash
pip install flask pytest colorama
```

> `colorama` is optional — only used for coloured terminal output in `demo_workflow.py`.

### 3. Run the web application

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

The SQLite database (`campus_network.db`) is created automatically on first run with all seed data.

---

## How to Demo

### Web Interface

| URL | Description |
|-----|-------------|
| `http://localhost:5000/` | Home / landing page |
| `http://localhost:5000/submit` | Submit a complaint (live DFA preview) |
| `http://localhost:5000/dashboard` | User dashboard (track by ID) |
| `http://localhost:5000/admin-dashboard` | Admin complaint management |
| `http://localhost:5000/routing` | Routing & priority queue |
| `http://localhost:5000/analytics` | Charts and stats |
| `http://localhost:5000/dfa-simulator` | DFA step-by-step simulator |

### CLI Demo (all steps in one go)

```bash
python demo_workflow.py
```

This prints each step: validate → classify → route → assign → update → resolve.

### Run Tests

```bash
pytest tests/ -v
```

Expected: **26 passed**.

---

## Key Features

### Part A – Automata Theory (BCS503)

**DFA Validator** (`services/dfa_validator.py`)
- Explicit state-transition table built programmatically
- Accepts: `(WIFI|LAN)-(HOST|LAB|ADM|LIB|CANT|SPRT)-[0-9]`
- Returns full step-by-step path for the simulator UI

**Regex Validator** (`services/regex_validator.py`)
- Pattern: `^(WIFI|LAN)-(HOST|LAB|ADM|LIB|CANT|SPRT)-[0-9]$`
- Compared against DFA result; agreement shown in UI

**Classifier** (`services/classifier.py`)
- 5 categories: Security, Hardware, Connectivity, Configuration, Unknown
- Priority: Security > Hardware > Connectivity > Configuration (multi-keyword)

### Part B – Computer Networks (BCS502)

**Routing Table** (`services/routing.py`)
```
HOST → HOSTEL   LAB → LAB   ADM → ADMIN
LIB  → LIB      CANT → CANTEEN   SPRT → SPORTS
```

**Routing Algorithm** (`services/routing_service.py`)
1. Extract location prefix from validated identifier
2. Map to zone → find primary admin
3. If primary Busy → try backup admin
4. If all zone admins Busy → try central admin
5. If all busy → priority queue (`ORDER BY priority weight, created_at`)
6. When admin becomes Available → auto-assign top of queue

### Part C – Web Application

- **Bootstrap 5** + custom CSS (indigo/teal palette, NO red anywhere)
- Live identifier preview with DFA+Regex validation (fetch API, no reload)
- Live category prediction as user types description
- AJAX status updates and admin availability toggle
- Chart.js bar + doughnut charts for analytics
- Animated count-up stat cards
- Status timeline stepper (Pending → Assigned → In Progress → Resolved)
- DFA Simulator with animated state path
- Dark mode toggle (persisted in localStorage)
- Fully responsive (mobile-friendly)

### Part D – Testing

- 26 pytest test cases in `tests/test_all.py`
- Each DB test uses an isolated temp SQLite file
- Full report in `TEST_REPORT.md`

---

## Business Rules Summary

| Rule | Implementation |
|------|---------------|
| Identifier format | `[DEVICE_TYPE]-[LOCATION_CODE]-[FLOOR]` |
| Valid device types | WIFI, LAN |
| Valid location codes | HOST, LAB, ADM, LIB, CANT, SPRT |
| Valid floors | 0–9 (single digit only) |
| Validation | BOTH DFA and regex must agree and accept |
| Priority | Security=High > Hardware=High > Connectivity=Medium > Configuration=Low > Unknown=Low |
| Admin assignment | Primary → Backup → Central → Queue |
| Queue ordering | Priority weight, then submission time (FIFO within same priority) |
| Auto-assign | Triggered when any admin switches to Available or resolves a complaint |

---

## Color System (No Red Rule)

| Element | Color |
|---------|-------|
| Primary / indigo | `#4f46e5` |
| Teal (secondary) | `#0d9488` |
| Priority High | Deep orange `#ea580c` |
| Priority Medium | Amber `#d97706` |
| Priority Low | Emerald `#059669` |
| Status Pending | Amber |
| Status Assigned | Indigo |
| Status In Progress | Teal |
| Status Resolved | Emerald |
| Admin Available | Emerald |
| Admin Busy | Slate gray |
| Errors / invalid | Orange (Bootstrap `danger` overridden) |

---

## Screenshots Checklist

- [ ] Home page hero section with live stats
- [ ] Complaint submission form with live identifier preview
- [ ] Submission success card with Complaint ID
- [ ] User Dashboard with status stepper
- [ ] Admin Dashboard with AJAX status dropdowns
- [ ] Routing Dashboard showing zone cards and priority queue
- [ ] Analytics Dashboard with Chart.js charts
- [ ] DFA Simulator animated state walk-through

---

## Viva Explanation Points

1. **DFA states** – 19 numbered states + trap state (-1) + accept state (18). Each transition encodes one character of the grammar.
2. **Regex equivalence** – The regex `^(WIFI|LAN)-(HOST|LAB|ADM|LIB|CANT|SPRT)-[0-9]$` is equivalent to the DFA by construction (same language).
3. **Classifier priority** – The `PRIORITY_ORDER` list resolves multi-keyword matches; Security always wins.
4. **Routing fallback chain** – Primary → Backup → Central → Queue. Each level is tried in `_find_admin()`.
5. **Priority queue** – Implemented as an `ORDER BY CASE priority ... END, created_at` SQL query (equivalent to a min-heap by weight).
6. **Auto-assign trigger** – Called from both `toggle_admin_availability()` and `update_complaint_status()` on Resolved.
