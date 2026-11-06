"""Explicit read-only enterprise tool registry; no model-selected tenant context."""
from dataclasses import dataclass
import logging
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.db.models import Customer, Document, Ticket, User
from app.monitoring.tracing import span


logger = logging.getLogger("copilot.tools")


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListArguments(Arguments):
    limit: int = Field(20, ge=1, le=50, strict=True)


class TicketListArguments(ListArguments):
    status: Literal["open", "in_progress", "closed"] | None = None


class TicketGetArguments(Arguments):
    ticket_id: int = Field(gt=0, strict=True)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    arguments: type[BaseModel]
    roles: tuple[str, ...] = ("user", "admin")
    timeout_ms: int = 1000


TOOLS = {
    tool.name: tool for tool in (
        ToolSpec("tickets.list", "List this tenant's ticket summaries", TicketListArguments),
        ToolSpec("tickets.get", "Read one authorized ticket summary", TicketGetArguments),
        ToolSpec("documents.list", "List this tenant's document metadata", ListArguments),
        ToolSpec("customers.current", "Read current tenant metadata", Arguments),
    )
}


class ToolNotFound(LookupError):
    pass


class ToolUnavailable(RuntimeError):
    pass


def list_tools(role):
    return [{"name": tool.name, "description": tool.description, "read_only": True,
             "timeout_ms": tool.timeout_ms, "input_schema": tool.arguments.model_json_schema()}
            for tool in TOOLS.values() if role in tool.roles]


def execute_tool(db, user, name, arguments):
    spec = TOOLS.get(name)
    if spec is None:
        raise ToolNotFound("Tool not found")
    parsed = spec.arguments.model_validate(arguments)
    identity = (user.id, user.customer_id)
    started = perf_counter()
    outcome = "failed"
    try:
        with span("agent.tool"):
            factory = sessionmaker(bind=db.get_bind(), autoflush=False)
            with factory() as tool_db:
                # Actual PostgreSQL query cancellation, not merely an elapsed-time
                # check. No caller session commit, rollback or timeout mutation.
                tool_db.execute(text(f"SET LOCAL statement_timeout = '{spec.timeout_ms}ms'"))
                active = tool_db.get(User, identity[0])
                if not active or not active.is_active or active.customer_id != identity[1] or active.role not in spec.roles:
                    raise PermissionError("Tool access denied")
                tenant = active.customer_id
                if name == "tickets.list":
                    statement = select(Ticket.id, Ticket.subject, Ticket.status, Ticket.priority).where(Ticket.customer_id == tenant)
                    if parsed.status:
                        statement = statement.where(Ticket.status == parsed.status)
                    rows = tool_db.execute(statement.order_by(Ticket.id).limit(parsed.limit)).mappings().all()
                elif name == "tickets.get":
                    rows = tool_db.execute(select(Ticket.id, Ticket.subject, Ticket.status, Ticket.priority)
                        .where(Ticket.customer_id == tenant, Ticket.id == parsed.ticket_id)).mappings().all()
                    if not rows:
                        raise ToolNotFound("Record not found")
                elif name == "documents.list":
                    rows = tool_db.execute(select(Document.id, Document.title, Document.created_at)
                        .where(Document.customer_id == tenant).order_by(Document.id).limit(parsed.limit)).mappings().all()
                else:
                    rows = tool_db.execute(select(Customer.id, Customer.name).where(Customer.id == tenant)).mappings().all()
                outcome = "completed"
                return {"tool": name, "items": [dict(row) for row in rows]}
    except (PermissionError, ToolNotFound):
        outcome = "denied"
        raise
    except Exception:
        raise ToolUnavailable("Tool temporarily unavailable") from None
    finally:
        logger.info("tool_call tool=%s outcome=%s duration_ms=%.3f", name, outcome, (perf_counter() - started) * 1000)
