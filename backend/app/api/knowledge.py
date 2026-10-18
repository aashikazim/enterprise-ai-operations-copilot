from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document, DocumentChunk, User
from app.auth.dependencies import require_admin
from app.services.chunking import chunk_text
from app.services.embedding_service import embed_text
from sqlalchemy import select
from app.auth.dependencies import get_current_user
from app.services.retrieval_service import retrieve_chunks

router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge Base"],
)


class DocumentIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


@router.post("/documents", status_code=201)
def ingest_document(
    data: DocumentIngestRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not data.content.strip():
        raise HTTPException(
            status_code=422,
            detail="Document content cannot be empty",
        )

    document = Document(
        title=data.title,
        content=data.content,
        customer_id=admin.customer_id,
    )

    db.add(document)
    db.flush()

    chunks = chunk_text(data.content)

    for index, chunk in enumerate(chunks):
        db.add(
            DocumentChunk(
                document_id=document.id,
                customer_id=admin.customer_id,
                chunk_index=index,
                content=chunk,
                embedding=embed_text(chunk),
            )
        )

    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "title": document.title,
        "chunks_created": len(chunks),
    }

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/search")
def search_knowledge(
    data: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = retrieve_chunks(
        db=db,
        query=data.query,
        customer_id=user.customer_id,
        top_k=data.top_k,
    )

    return {
        "query": data.query,
        "results": results,
    }