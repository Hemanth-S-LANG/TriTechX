"""
Validation Service
==================
Wraps the DFA and regex validators (Part A) together.
Builds the identifier from separate form fields and runs both validators,
reporting whether they agree.
"""
from services.dfa_validator import dfa_validate
from services.regex_validator import regex_validate

VALID_DEVICE_TYPES  = {"WIFI", "LAN"}
VALID_LOCATION_CODES = {"HOST", "LAB", "ADM", "LIB", "CANT", "SPRT"}


def build_identifier(device_type: str, location_code: str, floor: str) -> str:
    """Assemble the three fields into a location identifier string."""
    return f"{device_type.upper()}-{location_code.upper()}-{floor}"


def validate_identifier(device_type: str, location_code: str, floor: str) -> dict:
    """
    Build identifier and validate with BOTH DFA and regex.
    Returns:
      {
        "identifier":   str,
        "dfa_result":   dict,   # from dfa_validate()
        "regex_result": dict,   # from regex_validate()
        "both_agree":   bool,   # True when both give the same valid/invalid verdict
        "is_valid":     bool,   # True only when BOTH say valid
        "message":      str,
      }
    """
    identifier  = build_identifier(device_type, location_code, floor)
    dfa_result  = dfa_validate(identifier)
    reg_result  = regex_validate(identifier)

    both_agree = dfa_result["valid"] == reg_result["valid"]
    is_valid   = dfa_result["valid"] and reg_result["valid"]

    if is_valid:
        message = f"'{identifier}' is VALID — DFA ✓  Regex ✓"
    elif not both_agree:
        # Should never happen with a correctly built DFA and regex,
        # but we surface it if it does for academic interest.
        message = (
            f"'{identifier}' — DFA and regex DISAGREE. "
            f"DFA: {'valid' if dfa_result['valid'] else 'invalid'}, "
            f"Regex: {'valid' if reg_result['valid'] else 'invalid'}"
        )
    else:
        message = f"'{identifier}' is INVALID — rejected by both DFA and regex"

    return {
        "identifier":   identifier,
        "dfa_result":   dfa_result,
        "regex_result": reg_result,
        "both_agree":   both_agree,
        "is_valid":     is_valid,
        "message":      message,
    }


def quick_validate(identifier: str) -> dict:
    """
    Validate a pre-built identifier string directly.
    Useful for the DFA Simulator page and tests.
    """
    dfa_result  = dfa_validate(identifier)
    reg_result  = regex_validate(identifier)
    both_agree  = dfa_result["valid"] == reg_result["valid"]
    is_valid    = dfa_result["valid"] and reg_result["valid"]

    return {
        "identifier":   identifier,
        "dfa_result":   dfa_result,
        "regex_result": reg_result,
        "both_agree":   both_agree,
        "is_valid":     is_valid,
        "message":      (
            "Valid" if is_valid
            else "Invalid" if both_agree
            else "DFA and regex disagree"
        ),
    }
