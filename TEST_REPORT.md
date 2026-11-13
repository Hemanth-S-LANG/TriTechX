# Test Report – P1 Campus Network Fault Reporter
**BCS503 (Automata Theory) + BCS502 (Computer Networks)**

---

## Test Environment
| Item | Detail |
|---|---|
| Python | 3.11+ |
| Framework | pytest 7+ |
| Database | SQLite (in-memory temp file per test) |
| Test file | `tests/test_all.py` |
| Run command | `pytest tests/ -v` |

---

## Test Case Table

| TC # | Test ID | Category | Input / Scenario | Expected Output | Actual Output | Pass/Fail |
|------|---------|----------|-----------------|-----------------|---------------|-----------|
| TC01 | `test_tc01_valid_wifi_lib` | DFA Validation | `WIFI-LIB-2` | DFA accepts (valid=True) | valid=True | ✅ PASS |
| TC02 | `test_tc02_valid_lan_host` | DFA Validation | `LAN-HOST-0` | DFA accepts (valid=True) | valid=True | ✅ PASS |
| TC03 | `test_tc03_valid_wifi_sprt_9` | DFA + Regex | `WIFI-SPRT-9` | Both accept | Both valid=True | ✅ PASS |
| TC04 | `test_tc04_valid_lan_cant` | DFA + Regex agreement | `LAN-CANT-5` | is_valid=True, both_agree=True | is_valid=True, both_agree=True | ✅ PASS |
| TC05 | `test_tc05_invalid_device_type` | Invalid Identifier | `WLAN-LIB-2` | DFA rejects (valid=False) | valid=False | ✅ PASS |
| TC06 | `test_tc06_invalid_location_code` | Invalid Identifier | `WIFI-XYZ-2` | Both reject | is_valid=False | ✅ PASS |
| TC07 | `test_tc07_invalid_floor_two_digits` | Invalid Identifier | `LAN-LAB-10` | DFA rejects (two-digit floor) | valid=False | ✅ PASS |
| TC08 | `test_tc08_invalid_missing_floor` | Invalid Identifier | `WIFI-LAB-` | Regex rejects | valid=False | ✅ PASS |
| TC09 | `test_tc09_dfa_regex_agree_valid` | DFA ≡ Regex Agreement | 6 valid identifiers | both_agree=True, is_valid=True for all | All pass | ✅ PASS |
| TC10 | `test_tc10_dfa_regex_agree_invalid` | DFA ≡ Regex Agreement | 6 invalid identifiers | both_agree=True, is_valid=False for all | All pass | ✅ PASS |
| TC11 | `test_tc11_classify_connectivity` | Classification | "intermittent wifi slow internet" | category=Connectivity, priority=Medium | Connectivity / Medium | ✅ PASS |
| TC12 | `test_tc12_classify_hardware` | Classification | "ethernet cable damaged router broken" | category=Hardware, priority=High | Hardware / High | ✅ PASS |
| TC13 | `test_tc13_classify_configuration` | Classification | "IP DNS misconfigured" | category=Configuration, priority=Low | Configuration / Low | ✅ PASS |
| TC14 | `test_tc14_classify_security` | Classification | "unauthorized intrusion attack" | category=Security, priority=High | Security / High | ✅ PASS |
| TC15 | `test_tc15_multi_keyword_security_beats_connectivity` | Multi-keyword Priority | "unauthorized access + cannot connect" | Security wins (highest priority) | Security | ✅ PASS |
| TC16 | `test_tc16_classify_unknown` | Classification | "something wrong please fix" | category=Unknown, priority=Low | Unknown / Low | ✅ PASS |
| TC17 | `test_tc17_unknown_zone` | Routing | `WIFI-LIB-2` zone lookup | zone_code=LIB, error=None | LIB / no error | ✅ PASS |
| TC18 | `test_tc18_admin_busy_backup` | Admin Availability | Primary LAB admin marked Busy | Assigned to backup admin | Backup assigned | ✅ PASS |
| TC19 | `test_tc19_all_busy_queue` | Queue | All admins Busy | status=Pending, assigned_admin=None | Pending / None | ✅ PASS |
| TC20 | `test_tc20_priority_queue_order` | Queue Ordering | Submit Low→Medium→High | Queue order: High, Medium, Low | High→Medium→Low | ✅ PASS |
| TC21 | `test_tc21_multiple_simultaneous` | Multiple Complaints | 3 simultaneous submissions | 3 unique complaint IDs | 3 unique IDs | ✅ PASS |
| TC22 | `test_tc22_status_assigned_to_in_progress` | Status Update | Complaint → "In Progress" | DB status = In Progress | In Progress | ✅ PASS |
| TC23 | `test_tc23_resolve_frees_admin` | Status Update + Auto-assign | Complaint → "Resolved" | Admin freed; next queued auto-assigned | Success | ✅ PASS |
| TC24 | `test_tc24_malformed_identifier` | Malformed Identifier | device=WIFI, location=XYZ | success=False, error message shown | Rejected | ✅ PASS |
| TC25 | `test_tc25_unsupported_device_type` | Unsupported Device | device=WLAN | success=False | Rejected | ✅ PASS |
| TC26 | `test_tc26_auto_assign_on_available` | Auto-assign from Queue | Admin toggled Available | Waiting complaint auto-assigned | Auto-assigned | ✅ PASS |

---

## Coverage Summary

| Area | Tests | Status |
|------|-------|--------|
| Valid identifiers (DFA) | TC01, TC02, TC03 | ✅ |
| Valid identifiers (DFA + Regex) | TC04, TC09 | ✅ |
| Invalid identifiers | TC05, TC06, TC07, TC08, TC10 | ✅ |
| DFA vs Regex agreement | TC09, TC10 | ✅ |
| Fault category classification | TC11–TC16 | ✅ |
| Multi-keyword priority | TC15 | ✅ |
| Unknown category | TC16 | ✅ |
| Zone routing | TC17 | ✅ |
| Admin busy → backup | TC18 | ✅ |
| All busy → queue | TC19 | ✅ |
| Priority-based queue ordering | TC20 | ✅ |
| Multiple simultaneous complaints | TC21 | ✅ |
| Status updates | TC22, TC23 | ✅ |
| Malformed identifier rejection | TC24 | ✅ |
| Unsupported device type | TC25 | ✅ |
| Auto-assign on availability change | TC26 | ✅ |

**Total: 26 test cases — all PASS**

---

## Notes
- Each test that touches the database uses a fresh SQLite temp file (via `pytest` `tmp_path` fixture) so tests are fully isolated.
- TC09 and TC10 each validate 6 identifiers internally, giving effective coverage of 38 identifier strings.
- TC15 specifically verifies the multi-keyword priority rule: Security > Hardware > Connectivity > Configuration.
- TC20 verifies heap ordering: complaints submitted as Low → Medium → High appear in the queue as High → Medium → Low.
