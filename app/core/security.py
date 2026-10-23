import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

settings = get_settings()
_hasher = PasswordHasher()

ACCESS = "access"
REFRESH = "refresh"


@dataclass
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _issue(subject: int, token_type: str, lifetime: timedelta) -> IssuedToken:
    now = datetime.now(timezone.utc)
    expires = now + lifetime
    jti = uuid.uuid4().hex
    payload = {"sub": str(subject), "type": token_type, "jti": jti, "iat": now, "exp": expires}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return IssuedToken(token=token, jti=jti, expires_at=expires.replace(tzinfo=None))


def create_access_token(user_id: int) -> IssuedToken:
    return _issue(user_id, ACCESS, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: int) -> IssuedToken:
    return _issue(user_id, REFRESH, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc
    if payload.get("type") != expected_type or "sub" not in payload or "jti" not in payload:
        raise AuthenticationError("Invalid token type")
    return payload
