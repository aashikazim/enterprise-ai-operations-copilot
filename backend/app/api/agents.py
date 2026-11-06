import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.rag import RAGResponse
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.services.agent_service import AgentDeadlineExceeded, run_agent


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
    mode: Literal["read_only"]
    intent: Literal["knowledge", "unsupported_action"]
    result: RAGResponse
    steps: list[AgentStep]


@router.post("/run", response_model=AgentResponse)
def agent_run(data: AgentRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return run_agent(db, user, data.question, data.top_k)
    except AgentDeadlineExceeded:
        raise HTTPException(504, "Agent deadline exceeded") from None
    except PermissionError:
        raise HTTPException(403, "Agent authorization revoked") from None
    except (OpenAIError, RuntimeError):
        logger.error("Agent execution failed")
        raise HTTPException(503, "Agent temporarily unavailable") from None
