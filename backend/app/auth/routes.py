from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Request
from app.auth.limiter import limiter
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Customer, User
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    customer_id: int


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    customer_id: int


# DISABLED: Public registration allows arbitrary customer_id selection.
# Keep this implementation for local experiments only.
#
# To restore the old endpoint, uncomment the decorator below.
# WARNING: Do not enable it in a publicly accessible multi-tenant system.
#
# @router.post("/register", response_model=UserResponse, status_code=201)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    if not db.get(Customer, data.customer_id):
        raise HTTPException(404, "Customer not found")

    existing = db.scalar(
        select(User).where(User.email == data.email)
    )

    if existing:
        raise HTTPException(409, "Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        customer_id=data.customer_id,
        role="user",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        customer_id=user.customer_id,
    )


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == form.username)
    )

    if (
        user is None
        or not verify_password(form.password, user.hashed_password)
        or not user.is_active
    ):
        raise HTTPException(401, "Invalid credentials")

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }