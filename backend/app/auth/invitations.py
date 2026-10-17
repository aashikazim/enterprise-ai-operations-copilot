import hashlib
import secrets
from datetime import datetime, timedelta, timezone


INVITATION_EXPIRY_HOURS = 24


def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invitation_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        hours=INVITATION_EXPIRY_HOURS
    )