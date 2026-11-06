"""Synthetic local measurements, not a live model/load or cost benchmark."""
from statistics import median
from time import perf_counter

from app.db.models import Customer
from app.services import bm25_retrieval_service as service
from tests.test_bm25_retrieval import seed_chunks


def test_cached_index_isolation_and_content_invalidation(db, test_customer, monkeypatch):
    monkeypatch.setattr(service.get_settings(), 'rag_bm25_cache_enabled', True)
    service._cached_index.cache_clear()
    first = seed_chunks(db, test_customer.id, ['ERR_ALPHA recovery'])
    other = Customer(name='Synthetic other', email='other-cache@example.test')
    db.add(other)
    db.commit()
    second = seed_chunks(db, other.id, ['ERR_ALPHA recovery'])
    assert service.bm25_search(db, 'ERR_ALPHA', test_customer.id)[0]['chunk_id'] == first[0].id
    assert service.bm25_search(db, 'ERR_ALPHA', other.id)[0]['chunk_id'] == second[0].id
    assert service._cached_index.cache_info().misses == 2
    first[0].content = 'ERR_BETA recovery'
    db.commit()
    assert service.bm25_search(db, 'ERR_ALPHA', test_customer.id) == []
    assert service.bm25_search(db, 'ERR_BETA', test_customer.id)[0]['chunk_id'] == first[0].id
    db.delete(first[0])
    db.commit()
    assert service.bm25_search(db, 'ERR_BETA', test_customer.id) == []
    service._cached_index.cache_clear()


def test_reproducible_bm25_benchmark(db, test_customer, monkeypatch):
    contents = [f'ERR_CASE_{i} synthetic support procedure ' + 'operations recovery policy ' * 25 for i in range(200)]
    chunks = seed_chunks(db, test_customer.id, contents)
    expected = chunks[73].id
    results = {}
    for enabled in (False, True):
        service._cached_index.cache_clear()
        monkeypatch.setattr(service.get_settings(), 'rag_bm25_cache_enabled', enabled)
        service.bm25_search(db, 'ERR_CASE_73', test_customer.id)  # warm DB/index
        durations = []
        for _ in range(30):
            start = perf_counter()
            answer = service.bm25_search(db, 'ERR_CASE_73', test_customer.id, 5)
            durations.append((perf_counter() - start) * 1000)
            assert [row['chunk_id'] for row in answer] == [expected]
        results[enabled] = (median(durations), sorted(durations)[28])
    print(f'BM25 synthetic 200 chunks/30 searches: disabled p50/p95_ms={results[False]}; enabled={results[True]}; Recall@5=1 MRR=1 errors=0')
    # No timing assertion: machine contention must not make CI flaky.
    service._cached_index.cache_clear()


def test_authenticated_http_orchestration_baseline(client, user_headers, monkeypatch):
    from app.services.rag_service import build_rag_result
    result = build_rag_result('Synthetic answer', [])
    monkeypatch.setattr('app.api.rag.answer_question', lambda **kwargs: result)
    monkeypatch.setattr('app.services.agent_service.answer_question', lambda **kwargs: result)
    for path in ['/rag/ask', '/agents/run']:
        durations = []
        for _ in range(30):
            start = perf_counter()
            response = client.post(path, headers=user_headers, json={'question': 'Synthetic support question'})
            durations.append((perf_counter() - start) * 1000)
            assert response.status_code == 200
            body = response.json()
            assert (body['result'] if path == '/agents/run' else body)['answer'] == 'Synthetic answer'
        print(f'Authenticated orchestration {path} n=30 p50_ms={median(durations):.3f} p95_ms={sorted(durations)[28]:.3f} errors=0 model_calls=0')
