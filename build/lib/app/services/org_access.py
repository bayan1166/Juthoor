"""Organization membership proof.

An organization's slug is public (it appears in links and on screen). Knowing it must not be enough
to join as a teacher and read every student in the organization, so joining requires the
organization's join code. Only a SHA-256 of the code is stored (the code is high entropy, so a fast
hash is appropriate); the plain code is shown once when it is issued.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets


def _hash(code: str) -> str:
    return hashlib.sha256(code.strip().encode()).hexdigest()


def issue_join_code(org) -> str:
    """Generate (or rotate) the organization's join code and return the plain value once."""
    code = secrets.token_urlsafe(9)
    org.join_code_hash = _hash(code)
    return code


def code_matches(org, code: str | None) -> bool:
    if not code or not getattr(org, "join_code_hash", None):
        return False
    return hmac.compare_digest(org.join_code_hash, _hash(code))
