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
    query_vector = embed_text(data.query)

    distance = (
        DocumentChunk.embedding.cosine_distance(query_vector)
    )

    statement = (
        select(
            DocumentChunk,
            Document.title,
            distance.label("distance"),
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            DocumentChunk.customer_id == user.customer_id,
            Document.customer_id == user.customer_id,
        )
        .order_by(distance)
        .limit(data.top_k)
    )

    results = db.execute(statement).all()

    return {
        "query": data.query,
        "results": [
            {
                "document_id": chunk.document_id,
                "title": title,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "similarity": round(
                    max(0.0, min(1.0, 1 - float(dist))),
                    4,
                ),
            }
            for chunk, title, dist in results
        ],
    }