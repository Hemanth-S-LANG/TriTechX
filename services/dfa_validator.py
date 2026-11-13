"""
Part A – BCS503: DFA-based Location Identifier Validator
=========================================================
Validates identifiers in the format: [DEVICE_TYPE]-[LOCATION_CODE]-[FLOOR]
  DEVICE_TYPE   : WIFI | LAN
  LOCATION_CODE : HOST | LAB | ADM | LIB | CANT | SPRT
  FLOOR         : 0-9

The DFA is built explicitly with states and transition tables so it can be
shown step-by-step in the DFA Simulator page.
"""

# ---------------------------------------------------------------------------
# DFA definition
# ---------------------------------------------------------------------------

# Every character-by-character transition is captured so the simulator can
# replay the path.  States are integer labels; -1 is the dead/trap state.

STATES = list(range(0, 20)) + [-1]   # 0-19 valid + trap

# Transition table: dict[state][char] -> next_state
# Built programmatically for clarity and correctness.

def _build_transitions():
    t = {}
    def add(state, chars, next_state):
        t.setdefault(state, {})
        for c in chars:
            t[state][c] = next_state

    # --- DEVICE_TYPE ---
    # State 0: start
    add(0, 'W', 1)
    add(0, 'L', 5)

    # WIFI branch: W-I-F-I
    add(1, 'I', 2)
    add(2, 'F', 3)
    add(3, 'I', 4)

    # LAN branch: L-A-N
    add(5, 'A', 6)
    add(6, 'N', 7)

    # State 4 (after WIFI) and State 7 (after LAN) both expect '-'
    add(4, '-', 8)
    add(7, '-', 8)

    # --- LOCATION_CODE (state 8 = after first '-') ---
    # HOST: H-O-S-T
    add(8, 'H', 9)
    add(9, 'O', 10)
    add(10, 'S', 11)
    add(11, 'T', 16)   # -> second '-'

    # LAB: L-A-B
    add(8, 'L', 12)
    add(12, 'A', 13)
    add(13, 'B', 16)

    # ADM: A-D-M
    add(8, 'A', 20)
    add(20, 'D', 21)
    add(21, 'M', 16)

    # LIB: L-I-B  (share state 12 for 'L', diverge at 'I')
    add(12, 'I', 22)
    add(22, 'B', 16)

    # CANT: C-A-N-T
    add(8, 'C', 23)
    add(23, 'A', 24)
    add(24, 'N', 25)
    add(25, 'T', 16)

    # SPRT: S-P-R-T
    add(8, 'S', 26)
    add(26, 'P', 27)
    add(27, 'R', 28)
    add(28, 'T', 16)

    # --- second '-' ---
    add(16, '-', 17)

    # --- FLOOR digit 0-9 ---
    add(17, '0123456789', 18)

    # State 18 is the ACCEPT state (end of string expected here)
    # Any extra character -> trap
    return t

TRANSITIONS = _build_transitions()

# States used by extra nodes added above (beyond 0-18)
# 20=A(adm1), 21=D(adm2), 22=I(lib2), 23=C(cant1),
# 24=A(cant2), 25=N(cant3), 26=S(sprt1), 27=P(sprt2), 28=R(sprt3)

ACCEPT_STATE = 18


def dfa_validate(identifier: str) -> dict:
    """
    Run the DFA on *identifier* and return a result dict:
      {
        "valid":   bool,
        "path":    [(char, from_state, to_state), ...],  # step-by-step trace
        "final_state": int,
        "message": str
      }
    """
    state = 0
    path = []

    for ch in identifier:
        next_state = TRANSITIONS.get(state, {}).get(ch, -1)
        path.append({"char": ch, "from": state, "to": next_state})
        state = next_state
        if state == -1:
            # Once in trap, record remaining chars as trap->trap
            remaining = identifier[len(path):]
            for rc in remaining:
                path.append({"char": rc, "from": -1, "to": -1})
            break

    valid = (state == ACCEPT_STATE)
    return {
        "valid": valid,
        "path": path,
        "final_state": state,
        "message": "Valid identifier" if valid else "Invalid identifier (DFA rejected)"
    }


def get_dfa_description() -> dict:
    """Return a human-readable description of the DFA for the simulator UI."""
    return {
        "states": list(range(0, 19)) + [20, 21, 22, 23, 24, 25, 26, 27, 28, -1],
        "accept_states": [ACCEPT_STATE],
        "start_state": 0,
        "description": (
            "DFA validates: (WIFI|LAN) - (HOST|LAB|ADM|LIB|CANT|SPRT) - [0-9]"
        )
    }
