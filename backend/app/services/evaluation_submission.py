"""Best-effort durable evaluation of the exact evidence used by RAG.

This module never calls an evaluator and never commits the caller's session.
"""
import hashlib
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.database import get_settings
from app.db.models import Document, DocumentChunk
from app.jobs.evaluation_queue import enqueue_evaluation
from app.monitoring.evaluation_metrics import record_enqueue
from app.monitoring.tracing import traced, current_trace_context


def sampled(request_id: str, rate: float) -> bool:
    """Stable uniform bucket for one server-generated opaque request ID."""
    if rate <= 0:
        return False
    if rate >= 1:
        return True
    bucket = int.from_bytes(hashlib.sha256(request_id.encode()).digest()[:8], "big")
    return bucket / 2**64 < rate


@traced("db.evaluation.verify_evidence")
def verified_evidence(db, chunks, customer_id):
    ids = [chunk.get("chunk_id") for chunk in chunks]
    if any(type(identifier) is not int for identifier in ids) or len(set(ids)) != len(ids):
        return None
    rows = db.execute(
        select(DocumentChunk, Document.title)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.id.in_(ids),
            DocumentChunk.customer_id == customer_id,
            Document.customer_id == customer_id,
        )
    ).all()
    found = {chunk.id: (chunk, title) for chunk, title in rows}
    evidence = []
    for source_id, snapshot in enumerate(chunks, 1):
        row = found.get(snapshot["chunk_id"])
        if row is None:
            return None
        chunk, title = row
        if any(snapshot.get(key) != expected for key, expected in (
            ("document_id", chunk.document_id), ("chunk_index", chunk.chunk_index),
            ("content", chunk.content), ("title", title),
        )):
            return None
        # Preserve original source order. The evaluator numbers this list from 1.
        evidence.append({
            "source_id": source_id, "chunk_id": chunk.id,
            "document_id": chunk.document_id, "chunk_index": chunk.chunk_index,
            "title": title, "content": chunk.content,
        })
    return evidence


@traced("evaluation.enqueue")
def submit_sampled_evaluation(db, *, question, result, chunks, customer_id, request_id):
    started = perf_counter()
    outcome = "enqueue_failed"
    try:
        settings = get_settings()
        if not settings.rag_eval_enabled:
            outcome = "disabled"
        elif result["abstained"]:
            outcome = "abstained"
        elif not chunks:
            outcome = "empty_evidence"
        elif not result["citation_validation"]["citations_valid"]:
            outcome = "invalid_citations"
        elif not sampled(request_id, settings.rag_eval_sample_rate):
            outcome = "not_sampled"
        else:
            factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
            with factory() as evaluation_db:
                evidence = verified_evidence(evaluation_db, chunks, customer_id)
                if evidence is None:
                    outcome = "invalid_evidence"
                else:
                    enqueue_evaluation(
                        evaluation_db, customer_id, question, result["answer"], evidence,
                        request_id=request_id, trace_context=current_trace_context(),
                    )
                    outcome = "enqueued"
    except Exception:
        # DB/provider exceptions can embed SQL parameters or customer content.
        # Failure closes/rolls back only the independent evaluation session.
        outcome = "enqueue_failed"
    finally:
        record_enqueue(outcome, request_id, started)
    return outcome
