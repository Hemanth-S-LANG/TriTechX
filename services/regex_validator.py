"""
Part A – BCS503: Regex-based Location Identifier Validator
============================================================
Regular expression that matches the same language as the DFA:
  [DEVICE_TYPE]-[LOCATION_CODE]-[FLOOR]
"""
import re

# Regex matching (WIFI|LAN)-(HOST|LAB|ADM|LIB|CANT|SPRT)-[0-9]
PATTERN = r"^(WIFI|LAN)-(HOST|LAB|ADM|LIB|CANT|SPRT)-[0-9]$"
COMPILED_REGEX = re.compile(PATTERN)


def regex_validate(identifier: str) -> dict:
    """
    Validate identifier using regex. Return result dict:
      {
        "valid": bool,
        "pattern": str,
        "message": str
      }
    """
    match = COMPILED_REGEX.match(identifier)
    return {
        "valid": bool(match),
        "pattern": PATTERN,
        "message": "Valid identifier" if match else "Invalid identifier (regex rejected)"
    }
