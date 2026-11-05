from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.evaluation_job_model import EvaluationJob
from app.monitoring import tracing
from app.services.faithfulness_service import ClaimAssessment, FaithfulnessAssessment
from app.workers.evaluation_worker import process_next_job
from test_evaluation_submission import evidence, enabled


@pytest.fixture
def traces(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "_provider", provider)
    settings = SimpleNamespace(tracing_enabled=True, otel_exporter_otlp_traces_endpoint="")
    monkeypatch.setattr(tracing, "get_settings", lambda: settings)
    yield exporter, settings
    provider.shutdown()


def test_trace_roundtrip_and_payload_privacy(client, db, test_customer, user_headers,
        evidence, enabled, traces, monkeypatch):
    exporter, _ = traces
    monkeypatch.setattr("app.services.rag_service.retrieve_rag_context", lambda **kwargs: evidence)
    llm = Mock()
    llm.responses.create.return_value = SimpleNamespace(output_text="MFA [Source 1].", usage=None)
    llm.responses.parse.return_value = SimpleNamespace(output_parsed=FaithfulnessAssessment(claims=[
        ClaimAssessment(claim="Synthetic claim", cited_source_ids=[1], verdict="supported", explanation="Synthetic")
    ]))
    monkeypatch.setattr("app.services.llm_service.get_openai_client", lambda: llm)
    parent = "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01"
    response = client.post("/rag/ask", headers={**user_headers, "traceparent": parent,
        "baggage": "private=SECRET", "tracestate": "private=SECRET"}, json={"question": "PRIVATE QUESTION"})
    assert response.status_code == 200
    job = db.scalar(select(EvaluationJob))
    assert set(job.trace_context) == {"traceparent"} and job.request_id
    assert job.trace_context["traceparent"].split("-")[1] == parent.split("-")[1]
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    assert process_next_job(factory, llm)
    spans = exporter.get_finished_spans()
    names = {s.name for s in spans}
    assert {"http.request", "rag.retrieval", "rag.generation", "llm.generate", "evaluation.enqueue",
            "db.evaluation.enqueue", "evaluation.worker", "llm.evaluate", "db.evaluation.complete"} <= names
    root = next(s for s in spans if s.name == "http.request")
    worker = next(s for s in spans if s.name == "evaluation.worker")
    assert root.context.trace_id == worker.context.trace_id == int(parent.split("-")[1], 16)
    assert worker.parent.span_id == int(job.trace_context["traceparent"].split("-")[2], 16)
    assert worker.attributes["queue.wait_seconds"] >= 0
    exported = repr([(s.name, dict(s.attributes), s.events) for s in spans])
    assert "PRIVATE" not in exported and "SECRET" not in exported
    assert user_headers["Authorization"] not in exported
    assert evidence[0]["content"] not in exported
    assert "http.route" in root.attributes


def test_exception_message_and_traceback_never_exported(traces):
    exporter, _ = traces
    with pytest.raises(ValueError):
        with tracing.span("test.failure", **{"prompt": "SECRET", "db.statement": "SECRET"}):
            raise ValueError("PRIVATE DOCUMENT")
    span = exporter.get_finished_spans()[0]
    assert span.status.status_code == StatusCode.ERROR
    assert span.events == ()
    assert dict(span.attributes) == {"error.type": "operation_failed"}
    assert span.status.description is None


def test_disabled_tracing_emits_nothing(traces):
    exporter, settings = traces
    settings.tracing_enabled = False
    with tracing.span("disabled"):
        assert tracing.current_trace_context() is None
    assert not exporter.get_finished_spans()


def test_enabled_without_collector_requires_no_network(monkeypatch):
    monkeypatch.setattr(tracing, "_provider", None)
    monkeypatch.setattr(tracing, "get_settings", lambda: SimpleNamespace(
        tracing_enabled=True, otel_exporter_otlp_traces_endpoint=""))
    provider = tracing.configure_tracing()
    try:
        with tracing.span("offline"):
            assert tracing.current_trace_context()
    finally:
        provider.shutdown()


@pytest.mark.parametrize("endpoint", ["file:///tmp/traces", "https://user:secret@example.com/v1/traces", "https://example.com/v1/traces?token=secret"])
def test_rejects_unsafe_export_urls(monkeypatch, endpoint):
    monkeypatch.setattr(tracing, "_provider", None)
    monkeypatch.setattr(tracing, "get_settings", lambda: SimpleNamespace(
        tracing_enabled=True, otel_exporter_otlp_traces_endpoint=endpoint))
    with pytest.raises(ValueError, match="credential-free"):
        tracing.configure_tracing()


def test_invalid_parent_is_ignored(traces):
    with tracing.span("invalid-parent", context=tracing.extract_trace_context({"traceparent": "SECRET"})):
        parent = tracing.current_trace_context()["traceparent"]
        assert "SECRET" not in parent and len(parent) == 55
