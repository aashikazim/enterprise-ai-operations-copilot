from datetime import timedelta
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.conversation_models import now


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(36))
    tool: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSONB)
    payload_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="requested")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=lambda: now() + timedelta(minutes=15))
    __table_args__ = (UniqueConstraint("customer_id", "requested_by", "idempotency_key", name="uq_approvals_idempotency"),)


class ApprovalEvent(Base):
    __tablename__ = "approval_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)
