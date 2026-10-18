from sqlalchemy.orm import Session

from app.services.llm_service import generate_answer
from app.services.hybrid_retrieval_service import hybrid_retrieve
from app.services.reranking_service import rerank_chunks
from app.evals.answer_quality import validate_citations
import uuid

from app.services.observability import measure_stage

ABSTENTION_MESSAGE = (
    "I could not find sufficient information in the "
    "available documents to answer this question."
)

def build_rag_result(
    answer: str,
    chunks: list[dict],
) -> dict:
    sources = [
        {
            "source_id": index,
            "document_id": chunk["document_id"],
            "title": chunk["title"],
            "chunk_index": chunk["chunk_index"],
            "similarity": chunk.get("similarity", 0.0),
        }
        for index, chunk in enumerate(chunks, start=1)
    ]

    citation_check = validate_citations(
        answer,
        {source["source_id"] for source in sources},
    )

    abstained = (
        answer.strip() == ABSTENTION_MESSAGE
    )

    if citation_check["invalid_source_ids"]:
        # Conservative policy: do not return an answer
        # containing fabricated source references.
        answer = ABSTENTION_MESSAGE
        abstained = True

    return {
        "answer": answer,
        "sources": sources,
        "abstained": abstained,
        "citation_validation": citation_check,
    }

def retrieve_rag_context(
    db,
    question: str,
    customer_id: int,
    top_k: int = 5,
    use_reranker: bool = True,
):

    candidates = hybrid_retrieve(
        db=db,
        query=question,
        customer_id=customer_id,
        top_k=20,
        candidate_k=20,
    )

    if use_reranker:
        return rerank_chunks(
            query=question,
            chunks=candidates,
            top_k=top_k,
        )

    return candidates[:top_k]

def build_context(chunks: list[dict]) -> str:
    sections = []

    for index, chunk in enumerate(chunks, start=1):
        sections.append(
            f"[Source {index}]\n"
            f"Document: {chunk['title']}\n"
            f"Document ID: {chunk['document_id']}\n"
            f"Chunk: {chunk['chunk_index']}\n"
            f"Content:\n{chunk['content']}"
        )

    return "\n\n".join(sections)


def answer_question(
    db: Session,
    question: str,
    customer_id: int,
    top_k: int = 5,
) -> dict:
    request_id = str(uuid.uuid4())
    with measure_stage("retrieval", request_id):
        chunks = retrieve_rag_context(
            db=db,
            question=question,
            customer_id=customer_id,
            top_k=top_k,
        )

    if not chunks:
        return build_rag_result(
            answer=ABSTENTION_MESSAGE,
            chunks=[],
        )

    context = build_context(chunks)

    with measure_stage("generation", request_id):
        answer = generate_answer(
            question=question,
            context=context,
        )

    

    return build_rag_result(
        answer=answer,
        chunks=chunks,
    )