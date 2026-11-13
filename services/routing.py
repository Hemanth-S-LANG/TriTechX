"""
Part B – BCS502: Routing Table and Routing Algorithm
======================================================
Routing table: location code prefix  ->  zone code
Zone map:      zone code             ->  zone name
Admin lookup is done against the live database (passed in by the caller).

This module is pure-logic (no DB access) so it can be unit-tested standalone.
The Flask service layer (routing_service.py) wraps it with DB calls.
"""

# ---------------------------------------------------------------------------
# Routing table: location-code -> zone code
# ---------------------------------------------------------------------------
ROUTING_TABLE = {
    "HOST": "HOSTEL",
    "LAB":  "LAB",
    "ADM":  "ADMIN",
    "LIB":  "LIB",
    "CANT": "CANTEEN",
    "SPRT": "SPORTS",
}

# Zone code -> human-readable zone name
ZONE_NAMES = {
    "HOSTEL":  "Hostels",
    "LAB":     "Laboratories",
    "ADMIN":   "Admin Block",
    "LIB":     "Library",
    "CANTEEN": "Canteen",
    "SPORTS":  "Sports Complex",
    "CENTRAL": "Central (Unknown Zone)",
}

# Priority levels used for queue ordering (lower number = higher priority)
PRIORITY_WEIGHT = {
    "High":   1,
    "Medium": 2,
    "Low":    3,
}


def extract_location_code(identifier: str) -> str | None:
    """
    Extract the LOCATION_CODE part from a validated identifier.
    Returns None if the identifier is malformed.
    Example: 'WIFI-LIB-2' -> 'LIB'
    """
    parts = identifier.split("-")
    # Must have exactly 3 parts; last part single digit
    if len(parts) != 3:
        return None
    device_type, loc_code, floor = parts
    if device_type not in ("WIFI", "LAN"):
        return None
    if loc_code not in ROUTING_TABLE:
        return None
    if not (len(floor) == 1 and floor.isdigit()):
        return None
    return loc_code


def get_zone_for_identifier(identifier: str) -> dict:
    """
    Given a validated identifier, return zone info.
      {
        "zone_code":  str | None,
        "zone_name":  str,
        "location_code": str | None,
        "error":      str | None
      }
    """
    loc_code = extract_location_code(identifier)
    if loc_code is None:
        return {
            "zone_code": None,
            "zone_name": "",
            "location_code": None,
            "error": f"Malformed identifier: '{identifier}'",
        }

    zone_code = ROUTING_TABLE.get(loc_code)
    if zone_code is None:
        # Shouldn't happen after DFA/regex pass, but handle gracefully
        return {
            "zone_code":     "CENTRAL",
            "zone_name":     ZONE_NAMES["CENTRAL"],
            "location_code": loc_code,
            "error":         f"Unknown zone for location code '{loc_code}'; routed to central.",
        }

    return {
        "zone_code":     zone_code,
        "zone_name":     ZONE_NAMES[zone_code],
        "location_code": loc_code,
        "error":         None,
    }


def build_complaint_id(date_str: str, sequence: int) -> str:
    """
    Generate unique complaint ID, e.g. CMP-20261113-0001
    date_str: 'YYYYMMDD'
    sequence: integer counter for the day
    """
    return f"CMP-{date_str}-{sequence:04d}"
