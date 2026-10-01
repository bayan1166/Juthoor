import secrets

WEAK_VALUES = {"", "change-me", "change-me-to-a-long-random-string", "secret", "password", "jwt-secret"}
MIN_LENGTH = 32


def weak_secret_reason(value):
    value = value or ""
    if value.strip().lower() in WEAK_VALUES or value.lower().startswith("replace_with"):
        return "JWT_SECRET is still a placeholder"
    if len(value) < MIN_LENGTH:
        return f"JWT_SECRET must be at least {MIN_LENGTH} characters"
    if len(set(value)) < 10:
        return "JWT_SECRET has too little variety"
    return None


def suggestion():
    return secrets.token_urlsafe(48)
