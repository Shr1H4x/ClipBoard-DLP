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
    # JWT: every standard token's first segment is base64url of '{"', which
    # always starts with "eyJ". Anchoring on that (plus reasonably sized
    # segments) avoids false positives on domains, versions and file names.
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("ipv4", re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # simple credit card (Visa/Mastercard/Amex-like lengths, Luhn not enforced)
    ("credit_card", re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b")),
    ("phone", re.compile(r"\b\+?\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b")),
    # password/secret assignment:  "password: hunter2"  "passwd = xyz"  "PASSWORD=..."
    ("password", re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE)),
    # prose style:  "the password is hunter2"  "password for account is abc"
    ("password", re.compile(r"\b(?:password|passwd|pwd)\s+(?:is|for|->)\s+\S+", re.IGNORECASE)),
    # generic secrets/tokens in assignment form
    ("secret_key", re.compile(
        r"\b(?:secret|api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|"
        r"private[_-]?key|session[_-]?id|refresh[_-]?token)\s*[:=]\s*\S+", re.IGNORECASE)),
    # .env style credential lines
    ("env_secret", re.compile(
        r"\b(?:DB_PASSWORD|DATABASE_PASSWORD|SECRET_KEY|API_KEY|AWS_ACCESS_KEY_ID|"
        r"AWS_SECRET_ACCESS_KEY|PRIVATE_KEY|CLIENT_SECRET)\s*=\s*\S+", re.IGNORECASE)),
    # OTP with context words, e.g. "your verification code is 482913"
    ("otp", re.compile(
        r"\b(?:one[- ]?time[- ]?(?:password|code)|otp|verification code|security code|"
        r"login code|auth(?:entication)? code|confirmation code|2fa|two[- ]?factor code)\b"
        r"[^\n]{0,40}?\b\d{4,8}\b", re.IGNORECASE)),
    # explicit PIN: "PIN: 1234"  "pin is 987654"
    ("pin", re.compile(r"\bpin\s*(?::|is|=)\s*\d{4,8}\b", re.IGNORECASE)),
]

# Tokens that embed these words plus digits/symbols are almost certainly
# credentials ("mypassword123", "secret_2024", "ApiToken_9x").
_PASSWORD_KEYWORDS = re.compile(
    r"(?:pass(?:word|wd)?|pwd|secret|token|credential)", re.IGNORECASE)

PATTERN_LABELS = {
    "email": "Email address",
    "aws_access_key": "AWS access key",
    "jwt": "JWT",
    "ipv4": "IP address",
    "ssn": "SSN",
    "credit_card": "Credit card",
    "phone": "Phone number",
    "password": "Password",
    "secret_key": "API key/secret",
    "env_secret": "Environment secret",
    "otp": "OTP",
    "pin": "PIN code",
    "password_like": "Password-like string",
}


def _is_password_like(token: str) -> bool:
    """Heuristic for bare, unlabeled credentials such as '_@B4g@mZ$RfyE3N'.

    A token is flagged only when it genuinely looks like a credential:
    - all four character classes (upper + lower + digit + symbol), or
    - a credential keyword ("password", "secret", "token"...) plus a digit
      or symbol, so compounds like "mypassword123" are still caught.
    This deliberately skips common mixed-case alphanumerics such as
    "iPhone15ProMax" or "Christmas2024", which are not credentials.
    """
    if not 6 <= len(token) <= 64:
        return False
    # Skip emails / URLs / file-ish tokens ("user4@example.com", "192.168.1.1")
    if "." in token and re.search(r"\.\w", token):
        return False
    has_lower  = bool(re.search(r"[a-z]", token))
    has_upper  = bool(re.search(r"[A-Z]", token))
    has_digit  = bool(re.search(r"\d", token))
    has_symbol = bool(re.search(r"[^A-Za-z0-9]", token))
    # strong shape: mixes all four classes, e.g. "_@B4g@mZ$RfyE3N"
    if has_lower and has_upper and has_digit and has_symbol and len(token) >= 8:
        return True
    # credential keyword + something non-alphabetic, e.g. "mypassword123"
    if (has_lower or has_upper) and (has_digit or has_symbol) and len(token) >= 6:
        if _PASSWORD_KEYWORDS.search(token):
            return True
    return False


def _find_password_like(text: str) -> List[Dict]:
    out: List[Dict] = []
    for m in re.finditer(r"\S+", text):
        token = m.group(0).strip(".,!?;:'\"()[]{}<>|/\\`~*&^%$#@+-=_:")
        if _is_password_like(token):
            out.append({
                'type': 'password_like',
                'label': PATTERN_LABELS['password_like'],
                'match': token,
                'span': m.span(),
                'source': 'regex',
            })
    return out

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

    # bare credentials with no label: '_@B4g@mZ$RfyE3N', 'mypassword123'
    out.extend(_find_password_like(text))

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
