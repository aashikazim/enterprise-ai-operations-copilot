import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from openai import OpenAIError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.rag_service import answer_question


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


class RAGRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000,
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )


class RAGSource(BaseModel):
    source_id: int
    document_id: int
    title: str
    chunk_index: int
    similarity: float


class CitationValidation(BaseModel):
    cited_source_ids: list[int] = Field(default_factory=list)
    invalid_source_ids: list[int] = Field(default_factory=list)
    citations_valid: bool = True
    has_citations: bool = False

class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    abstained: bool = False
    citation_validation: CitationValidation = Field(
        default_factory=CitationValidation
    )


@router.post("/ask", response_model=RAGResponse)
def ask_rag(
    request: RAGRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return answer_question(
            db=db,
            question=request.question,
            customer_id=user.customer_id,
            top_k=request.top_k,
        )

    except OpenAIError:
        logger.exception("LLM provider request failed")
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable",
        )

    except RuntimeError:
        logger.exception("RAG service configuration error")
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable",
        )