from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str


class CustomerResponse(CustomerCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    customer_id: int
    subject: str = Field(min_length=1)
    description: str
    priority: Literal["low", "medium", "high"] = "medium"


class TicketUpdate(BaseModel):
    status: Literal["open", "in_progress", "closed"]


class TicketResponse(TicketCreate):
    id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)