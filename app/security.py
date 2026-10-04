"""Password hashing and access tokens.

* Passwords: bcrypt (cost 12) via the `bcrypt` package directly. Hashes are standard `$2b$`
  strings, so hashes written by the earlier passlib-based version keep verifying.
  bcrypt only uses the first 72 bytes of a password; we truncate explicitly so behaviour is
  identical across bcrypt versions (4.x silently truncates, 5.x raises).
* Tokens: HS256 JWT via PyJWT (maintained, pure Python). Any malformed, expired or
  wrongly signed token decodes to None, which the API turns into 401 invalid_token.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

BCRYPT_ROUNDS = 12
_BCRYPT_MAX_BYTES = 72


def _secret_bytes(raw: str) -> bytes:
    return raw.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(_secret_bytes(raw), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(raw: str, hashed: str) -> bool:
    if not raw or not hashed:
        return False
    try:
        return bcrypt.checkpw(_secret_bytes(raw), hashed.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError):
        return False


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
