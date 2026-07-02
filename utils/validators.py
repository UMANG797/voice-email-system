"""
Input validation helpers — email format, password strength, generic sanitisation.
"""

import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def is_valid_email(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def is_strong_password(password: str) -> (bool, str):
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""


def clean_text(value: str, max_len: int = 5000) -> str:
    """Basic sanitisation: strip control characters and cap length.
    Jinja2 autoescaping in templates handles XSS on output; this guards storage/size."""
    if value is None:
        return ""
    value = value.strip()[:max_len]
    return "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
