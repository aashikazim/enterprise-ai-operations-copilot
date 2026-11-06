import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.rag import RAGResponse
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.services.agent_service import AgentDeadlineExceeded, run_agent
from app.services.tool_service import execute_tool, list_tools, ToolNotFound
from app.services.approval_service import ApprovalMissing, ApprovalConflict


router = APIRouter(prefix="/agents", tags=["Agents"])
logger = logging.getLogger(__name__)


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=10)


class AgentStep(BaseModel):
    node: str
    status: Literal["completed", "blocked"]


class AgentResponse(BaseModel):
    request_id: str
    mode: Literal["read_only", "approval_required"]
    intent: Literal["knowledge", "unsupported_action", "records", "approval_required", "connector_read"]
    result: RAGResponse
    steps: list[AgentStep]
    tool_results: list[dict] = Field(default_factory=list)
    approvals: list[dict] = Field(default_factory=list)


@router.post("/run", response_model=AgentResponse)
def agent_run(data: AgentRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return run_agent(db, user, data.question, data.top_k)
    except AgentDeadlineExceeded:
        raise HTTPException(504, "Agent deadline exceeded") from None
    except PermissionError:
        raise HTTPException(403, "Agent authorization revoked") from None
    except (ToolNotFound, ApprovalMissing):
        raise HTTPException(404, "Record not found") from None
    except ApprovalConflict:
        raise HTTPException(409, "Approval proposal conflict") from None
    except ValidationError:
        raise HTTPException(422, "Invalid tool arguments") from None
    except (OpenAIError, RuntimeError):
        logger.error("Agent execution failed")
        raise HTTPException(503, "Agent temporarily unavailable") from None


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arguments: dict = Field(default_factory=dict)


@router.get("/tools")
def tools(user=Depends(get_current_user)):
    return {"items": list_tools(user.role)}


@router.post("/tools/{name}")
def tool_call(name: str, data: ToolRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return execute_tool(db, user, name, data.arguments)
    except ToolNotFound:
        raise HTTPException(404, "Tool or record not found") from None
    except ValidationError:
        raise HTTPException(422, "Invalid tool arguments") from None
    except PermissionError:
        raise HTTPException(403, "Tool access denied") from None
    except RuntimeError:
        raise HTTPException(503, "Tool temporarily unavailable") from None
