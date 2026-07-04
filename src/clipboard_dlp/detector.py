from __future__ import annotations

import re
from typing import List, Dict, Optional, Any
import os

# Optional yara support
try:
    import yara
except Exception:
    yara = None


# Precompiled regex patterns for common sensitive formats
PATTERNS = [
    ("email", re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("jwt", re.compile(r"[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+")),
    ("ipv4", re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # simple credit card (Visa/Mastercard/Amex-like lengths, Luhn not enforced)
    ("credit_card", re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b")),
    ("phone", re.compile(r"\b\+?\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b")),
]

PATTERN_LABELS = {
    "email": "Email address",
    "aws_access_key": "AWS access key",
    "jwt": "JWT",
    "ipv4": "IP address",
    "ssn": "SSN",
    "credit_card": "Credit card",
    "phone": "Phone number",
}

SENSITIVE_COPY_PREFIX = "⚠️ Sensitive data copied"
SENSITIVE_COPY_HEADER = f"{SENSITIVE_COPY_PREFIX}\n\n"


def _humanize_rule_name(name: str) -> str:
    text = name.replace("_", " ").replace("-", " ").strip()
    if not text:
        return name
    return text[0].upper() + text[1:]


def _load_yara_rules(rules_dir: Optional[str]) -> Optional[Any]:
    if yara is None or not rules_dir:
        return None

    if not os.path.isdir(rules_dir):
        return None

    rules_files = [
        os.path.join(rules_dir, f)
        for f in sorted(os.listdir(rules_dir))
        if (f.endswith(".yar") or f.endswith(".yara"))
        and os.path.getsize(os.path.join(rules_dir, f)) > 0
    ]

    if not rules_files:
        return None

    try:
        return yara.compile(
            filepaths={
                f"rule_{i}": path
                for i, path in enumerate(rules_files)
            }
        )

    except yara.Error as e:
        print(f"YARA compilation failed: {e}")
        return None


def detect_sensitive(text: str, yara_rules_dir: Optional[str] = None) -> List[Dict]:
    """Return a list of detection dicts for the provided text.

    Each dict contains: `type`, `match`, `span`, `source`, and optionally `rule`.
    """
    out: List[Dict] = []
    if not text:
        return out

    for name, pat in PATTERNS:
        for m in pat.finditer(text):
            out.append({
                'type': name,
                'label': PATTERN_LABELS.get(name, _humanize_rule_name(name)),
                'match': m.group(0),
                'span': m.span(),
                'source': 'regex',
            })

    # YARA rules (optional)
    rules = _load_yara_rules(yara_rules_dir) if yara_rules_dir else None
    if rules is None and yara is not None and yara_rules_dir is None:
        # try default rules directory next to module
        here = os.path.dirname(__file__)
        default_dir = os.path.join(here, "yara")
        rules = _load_yara_rules(default_dir)

    if rules is not None:
        try:
            matches = rules.match(data=text)
            for m in matches:
                out.append({
                    'type': 'yara',
                    'label': _humanize_rule_name(m.rule),
                    'match': m.rule,
                    'rule': m.rule,
                    'tags': list(m.tags) if hasattr(m, 'tags') else [],
                    'source': 'yara',
                })
        except Exception:
            pass

    return out


def format_sensitive_copy(content: str, detections: Optional[List[Dict]] = None) -> str:
    if not content:
        return content
    if detections:
        return f"{SENSITIVE_COPY_HEADER}{content}"
    return content


def strip_sensitive_copy_prefix(content: str) -> str:
    if content.startswith(SENSITIVE_COPY_HEADER):
        return content[len(SENSITIVE_COPY_HEADER):]
    return content


def summarize_detections(detections: List[Dict]) -> str:
    labels: List[str] = []
    for item in detections:
        label = item.get('label') or item.get('rule') or item.get('type')
        if not label:
            continue
        if label not in labels:
            labels.append(label)
    return ", ".join(labels)
