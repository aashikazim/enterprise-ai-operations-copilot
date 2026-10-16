from datetime import datetime, timezone

from sqlalchemy import (
    DateTime, ForeignKey, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True
    )

    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="customer"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id")
    )
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), default="open"
    )
    priority: Mapped[str] = mapped_column(
        String(30), default="medium"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="tickets"
    )

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True
    )

    hashed_password: Mapped[str] = mapped_column(String(255))

    role: Mapped[str] = mapped_column(
        String(20), default="user", nullable=False
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        default=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )