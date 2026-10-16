from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Customer
from app.api.schemas import CustomerCreate, CustomerResponse
from app.auth.dependencies import get_current_user, require_admin
from app.db.models import User

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/", response_model=CustomerResponse, status_code=403)
def create_customer():
    raise HTTPException(
        403, "Customer creation requires platform provisioning"
    )


@router.get("/", response_model=list[CustomerResponse])
def list_customers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    customer = db.get(Customer, user.customer_id)
    return [customer] if customer else []


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if customer_id != user.customer_id:
        raise HTTPException(404, "Customer not found")

    customer = db.get(Customer, customer_id)

    if not customer:
        raise HTTPException(404, "Customer not found")

    return customer