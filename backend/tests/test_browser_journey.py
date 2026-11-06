"""Real Chromium + Vite + FastAPI + PostgreSQL journey; model seams are offline.

RUN_BROWSER_E2E=1 BROWSER_EXECUTABLE_PATH=/usr/bin/google-chrome pytest ...
Install frontend dev dependencies first. CI can use Playwright's bundled browser.
"""
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.request import urlopen
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
import uvicorn

from app.main import app
from app.db.database import get_db, get_settings
from app.db.models import Customer, Document, DocumentChunk, Ticket
from app.db.evaluation_job_model import EvaluationJob
from app.workers.evaluation_worker import process_next_job


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_http(url, process_alive):
    for _ in range(100):
        if not process_alive():
            raise AssertionError('Owned test server exited early')
        try:
            with urlopen(url, timeout=.3) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(.1)
    raise AssertionError('Owned test server did not become ready')


@pytest.mark.skipif(os.environ.get('RUN_BROWSER_E2E') != '1', reason='Opt-in Chromium/Vite integration; see docs/VERIFICATION.md')
def test_browser_enterprise_journey(db, test_admin, test_customer, monkeypatch):
    # The db fixture guards and owns only copilot_test_db. No server uses its Session.
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    ticket = Ticket(customer_id=test_customer.id, subject='Synthetic access incident', description='Synthetic only')
    other = Customer(name='Other synthetic tenant', email='browser-other@example.test')
    db.add_all([ticket, other])
    db.flush()
    foreign = Document(customer_id=other.id, title='Foreign synthetic', content='Forbidden data')
    db.add(foreign)
    db.flush()
    db.add(DocumentChunk(customer_id=other.id, document_id=foreign.id, chunk_index=0,
                         content='Forbidden data', embedding=[1.0] + [0.0]*383))
    db.commit()
    settings = get_settings()
    monkeypatch.setattr(settings, 'rag_eval_enabled', True)
    monkeypatch.setattr(settings, 'rag_eval_sample_rate', 1.0)
    vector = lambda text: [1.0] + [0.0]*383
    monkeypatch.setattr('app.api.knowledge.embed_text', vector)
    monkeypatch.setattr('app.services.retrieval_service.embed_text', vector)
    monkeypatch.setattr('app.services.rag_service.rerank_chunks', lambda query, chunks, top_k: chunks[:top_k])
    monkeypatch.setattr('app.services.rag_service.generate_answer', lambda **kwargs: 'Contact the synthetic help desk [Source 1].')
    def sessions():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = sessions
    api_port, ui_port = free_port(), free_port()
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=api_port, log_level='critical', access_log=False))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    frontend = Path(__file__).resolve().parents[2] / 'frontend'
    process = None
    try:
        wait_http(f'http://127.0.0.1:{api_port}/ready', thread.is_alive)
        environment = dict(os.environ, API_PROXY_TARGET=f'http://127.0.0.1:{api_port}')
        process = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(ui_port), '--strictPort'],
            cwd=frontend, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_http(f'http://127.0.0.1:{ui_port}', lambda: process.poll() is None)
        environment.update(E2E_ORIGIN=f'http://127.0.0.1:{ui_port}', E2E_TICKET_ID=str(ticket.id),
                           E2E_FOREIGN_DOCUMENT_ID=str(foreign.id))
        result = subprocess.run(['node', 'e2e/journey.mjs'], cwd=frontend, env=environment,
                                capture_output=True, text=True, timeout=90)
        assert result.returncode == 0, result.stdout + result.stderr
        print(result.stdout)
        evaluator = Mock(return_value={'claims': [{'claim': 'Synthetic claim', 'verdict': 'supported',
                             'cited_source_ids': [1], 'explanation': 'Synthetic mocked evaluator'}], 'faithfulness_score': 1.0})
        assert process_next_job(factory, None, evaluator)
        with factory() as session:
            assert session.get(Ticket, ticket.id).status == 'closed'
            job = session.scalar(select(EvaluationJob).where(EvaluationJob.customer_id == test_customer.id))
            assert job.status == 'completed' and job.result['faithfulness_score'] == 1.0
        print('Real worker consumed browser RAG job with mocked evaluator; score is fixture output, not measured model quality')
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        server.should_exit = True
        thread.join(timeout=5)
        app.dependency_overrides.clear()
