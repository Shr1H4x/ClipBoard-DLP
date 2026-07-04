import re
import math
from typing import List, Dict, Any

# Simple detection patterns (extensible)
PATTERNS = {
    "BTC_ADDRESS": re.compile(r"\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "ETH_ADDRESS": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "API_KEY_LIKE": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_]{8,}|AKIA[0-9A-Z]{8,})\b"),
    "EMAIL": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "OTP": re.compile(r"\b\d{4,8}\b"),
}


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    entropy = 0.0
    length = len(s)
    for v in freq.values():
        p = v / length
        entropy -= p * math.log2(p)
    return entropy


def detect(text: str) -> Dict[str, Any]:
    """Run simple pattern detection and entropy check on `text`.

    Returns a dict with keys: matches (list), entropy (float), risk (str)
    """
    matches: List[str] = []
    for name, pattern in PATTERNS.items():
        if pattern.search(text):
            matches.append(name)

    ent = shannon_entropy(text)

    # Simple risk assignment rules
    if "BTC_ADDRESS" in matches or "ETH_ADDRESS" in matches:
        risk = "CRITICAL"
    elif "API_KEY_LIKE" in matches or ent > 4.5:
        risk = "HIGH"
    elif "CREDIT_CARD" in matches or "OTP" in matches:
        risk = "HIGH"
    elif matches:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {"matches": matches, "entropy": ent, "risk": risk}
