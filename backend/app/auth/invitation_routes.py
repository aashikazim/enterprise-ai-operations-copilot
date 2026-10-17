from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.invitations import (
    generate_invitation_token,
    hash_invitation_token,
    invitation_expiry,
)
from app.auth.security import hash_password
from app.db.database import get_db
from app.db.models import Invitation, User

router = APIRouter(
    prefix="/auth/invitations",
    tags=["Invitations"],
)


class InvitationCreate(BaseModel):
    email: EmailStr


class InvitationAccept(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


@router.post("/", status_code=201)
def create_invitation(
    data: InvitationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    email = str(data.email).strip().lower()

    existing = db.scalar(
        select(User).where(User.email == email)
    )

    if existing:
        raise HTTPException(409, "User already exists")

    token = generate_invitation_token()

    invitation = Invitation(
        email=email,
        customer_id=admin.customer_id,
        role="user",
        token_hash=hash_invitation_token(token),
        expires_at=invitation_expiry(),
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # Local development only.
    # In production, send this token through an email service.
    return {
        "invitation_id": invitation.id,
        "token": token,
        "expires_at": invitation.expires_at,
    }


@router.post("/accept", status_code=201)
def accept_invitation(
    data: InvitationAccept,
    db: Session = Depends(get_db),
):
    token_hash = hash_invitation_token(data.token)
    now = datetime.now(timezone.utc)

    # Atomically claim the invitation so concurrent requests
    # cannot successfully redeem the same token twice.
    result = db.execute(
        update(Invitation)
        .where(
            Invitation.token_hash == token_hash,
            Invitation.used_at.is_(None),
            Invitation.expires_at > now,
        )
        .values(used_at=now)
        .returning(
            Invitation.email,
            Invitation.customer_id,
            Invitation.role,
        )
    )

    claimed = result.first()

    if claimed is None:
        db.rollback()
        raise HTTPException(
            400, "Invalid, expired, or used invitation"
        )

    user = User(
        email=claimed.email,
        customer_id=claimed.customer_id,
        role=claimed.role,
        hashed_password=hash_password(data.password),
        is_active=True,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Account already exists"
        )

    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "customer_id": user.customer_id,
    }