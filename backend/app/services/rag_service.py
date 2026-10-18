from sqlalchemy.orm import Session

from app.services.llm_service import generate_answer
from app.services.hybrid_retrieval_service import hybrid_retrieve
from app.services.reranking_service import rerank_chunks

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

    chunks = retrieve_rag_context(
        db=db,
        question=question,
        customer_id=customer_id,
        top_k=top_k,
    )

    if not chunks:
        return {
            "answer": (
                "I could not find relevant information "
                "in the available knowledge base."
            ),
            "sources": [],
        }

    context = build_context(chunks)

    answer = generate_answer(
        question=question,
        context=context,
    )

    sources = [
        {
            "source_id": index,
            "document_id": chunk["document_id"],
            "title": chunk["title"],
            "chunk_index": chunk["chunk_index"],
            "similarity": chunk["similarity"],
        }
        for index, chunk in enumerate(chunks, start=1)
    ]

    return {
        "answer": answer,
        "sources": sources,
    }