from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.encryption_key.encode("utf-8"))


def encrypt_text(value: str) -> str:
    if not value:
        return ""
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    if not value:
        return ""
    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt value") from exc

