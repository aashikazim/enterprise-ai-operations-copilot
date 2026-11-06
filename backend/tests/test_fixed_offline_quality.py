"""Fixed synthetic lexical/citation dataset; no semantic-model score claimed."""
from statistics import mean

from app.evals.retrieval_metrics import recall_at_k, reciprocal_rank
from app.services.bm25_retrieval_service import bm25_search
from app.services.rag_service import answer_question
from tests.test_bm25_retrieval import seed_chunks


def test_fixed_lexical_and_answer_contract_dataset(db, test_customer, monkeypatch):
    chunks = seed_chunks(db, test_customer.id, [
        'ERR_MFA_403 recovery requires identity verification.',
        'ERR_BACKUP_502 recovery requires storage review.',
        'Annual leave policy needs manager approval.',
    ])
    cases = [('ERR_MFA_403', chunks[0].id), ('ERR_BACKUP_502', chunks[1].id)]
    recalls, reciprocal_ranks, citation_passes = [], [], []
    monkeypatch.setattr('app.services.rag_service.retrieve_rag_context',
        lambda db, question, customer_id, top_k: bm25_search(db, question, customer_id, top_k))
    monkeypatch.setattr('app.services.rag_service.generate_answer', lambda **kwargs: 'Review the policy [Source 1].')
    monkeypatch.setattr('app.services.rag_service.submit_sampled_evaluation', lambda *args, **kwargs: 'disabled')
    for query, relevant in cases:
        rows = bm25_search(db, query, test_customer.id, 3)
        identifiers = [row['chunk_id'] for row in rows]
        recalls.append(recall_at_k(identifiers, {relevant}, 3))
        reciprocal_ranks.append(reciprocal_rank(identifiers, {relevant}))
        result = answer_question(db, query, test_customer.id, 3)
        citation_passes.append(result['citation_validation']['citations_valid'] and result['citation_validation']['has_citations'])
        assert not result['abstained']
    unknown = answer_question(db, 'UNSEEN_IDENTIFIER_999', test_customer.id, 3)
    assert unknown['abstained'] and not unknown['sources']
    assert mean(recalls) == mean(reciprocal_ranks) == 1
    assert all(citation_passes)
    print(f'Fixed lexical dataset relevant_cases={len(cases)} Recall@3={mean(recalls):.3f} MRR={mean(reciprocal_ranks):.3f} citation_contract={sum(citation_passes)}/{len(cases)} no_match_abstention=1/1; faithfulness/model_cost=not_measured')
