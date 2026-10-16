import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db, get_settings
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    error = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        settings = get_settings()

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = int(payload["sub"])

    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise error

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise error

    return user


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return user