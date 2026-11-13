"""
Part A – BCS503: Complaint Classifier
=======================================
Classifies complaint descriptions into:
  Security > Hardware > Connectivity > Configuration > Unknown

Priority mapping:
  Security      -> High
  Hardware      -> High
  Connectivity  -> Medium
  Configuration -> Low
  Unknown       -> Low

When multiple categories match, Security wins (highest priority).
"""

# Keyword sets for each category
KEYWORDS = {
    "Security":      ["unauthorized", "breach", "hack", "intrusion", "attack",
                      "malware", "virus", "suspicious", "password", "access denied",
                      "firewall", "blocked", "phishing"],
    "Hardware":      ["router", "switch", "cable", "port", "device", "broken",
                      "damaged", "hardware", "ethernet", "nic", "connector",
                      "physical", "burnt", "overheating", "blinking"],
    "Connectivity":  ["slow", "intermittent", "dropped", "no internet",
                      "cannot connect", "wifi down", "lan down", "disconnected",
                      "latency", "packet loss", "timeout", "unreachable",
                      "no signal", "weak signal", "ping"],
    "Configuration": ["ip", "dns", "dhcp", "subnet", "gateway", "vlan",
                      "configuration", "config", "setting", "misconfigured",
                      "address", "ssid", "proxy", "vpn", "protocol"],
}

# Priority order (highest first) used for multi-match resolution
PRIORITY_ORDER = ["Security", "Hardware", "Connectivity", "Configuration"]

# Category -> priority level
PRIORITY_MAP = {
    "Security":      "High",
    "Hardware":      "High",
    "Connectivity":  "Medium",
    "Configuration": "Low",
    "Unknown":       "Low",
}


def classify_complaint(description: str) -> dict:
    """
    Classify *description* and return:
      {
        "category":       str,
        "priority":       str,
        "matched_keywords": list[str],
        "all_matches":    dict[category -> [keywords]]
      }
    """
    text = description.lower()
    all_matches = {}

    for category, keywords in KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text]
        if hits:
            all_matches[category] = hits

    # Resolve by priority order
    category = "Unknown"
    for cat in PRIORITY_ORDER:
        if cat in all_matches:
            category = cat
            break

    matched_keywords = all_matches.get(category, [])

    return {
        "category":        category,
        "priority":        PRIORITY_MAP[category],
        "matched_keywords": matched_keywords,
        "all_matches":     all_matches,
    }


def get_priority_map() -> dict:
    """Expose the priority map for use in routing/db seeding."""
    return PRIORITY_MAP
