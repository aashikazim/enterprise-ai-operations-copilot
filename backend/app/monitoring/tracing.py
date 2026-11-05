"""Explicit OpenTelemetry spans with a small, content-free attribute allowlist.

No automatic SQL/HTTP body instrumentation or exception recording. Export is
optional and asynchronous. Only W3C traceparent crosses the queue boundary.
"""
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from urllib.parse import urlsplit

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.db.database import get_settings


_provider = None
_lock = Lock()
_propagator = TraceContextTextMapPropagator()
SAFE_ATTRIBUTES = frozenset({"request.id", "job.id", "job.attempt", "queue.wait_seconds",
    "http.request.method", "http.response.status_code", "http.route", "error.type"})


def configure_tracing(service_name="copilot-api"):
    global _provider
    if not get_settings().tracing_enabled:
        return None
    with _lock:
        if _provider is not None:
            return _provider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        provider = TracerProvider(resource=Resource({"service.name": service_name}))
        endpoint = get_settings().otel_exporter_otlp_traces_endpoint
        if endpoint:
            parsed = urlsplit(endpoint)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("OTLP endpoint must be a credential-free HTTP(S) URL")
            import requests
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            session = requests.Session()
            session.trust_env = False
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
                endpoint=endpoint, timeout=2, session=session,
            )))
        _provider = provider
        return provider


@contextmanager
def span(name, *, context=None, **attributes):
    provider = configure_tracing()
    tracer = provider.get_tracer("copilot") if provider else trace.NoOpTracer()
    safe = {key: value for key, value in attributes.items() if key in SAFE_ATTRIBUTES}
    with tracer.start_as_current_span(name, context=context, attributes=safe,
            record_exception=False, set_status_on_exception=False) as current:
        try:
            yield current
        except Exception:
            current.set_status(Status(StatusCode.ERROR))
            current.set_attribute("error.type", "operation_failed")
            raise


def traced(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with span(name):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def current_trace_context():
    carrier = {}
    if get_settings().tracing_enabled:
        _propagator.inject(carrier)
    return {"traceparent": carrier["traceparent"]} if "traceparent" in carrier else None


def extract_trace_context(carrier):
    parent = (carrier or {}).get("traceparent", "")
    # No baggage or tracestate; do not retain arbitrary incoming attributes.
    return _propagator.extract({"traceparent": parent}) if isinstance(parent, str) and len(parent) == 55 else _propagator.extract({})


class TracingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        carrier = {"traceparent": value.decode("ascii", errors="ignore")
                   for key, value in scope.get("headers", []) if key == b"traceparent"}
        with span("http.request", context=extract_trace_context(carrier)) as current:
            method = scope.get("method", "")
            current.set_attribute("http.request.method", method if method in {"GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS", "HEAD"} else "OTHER")
            async def traced_send(message):
                if message["type"] == "http.response.start":
                    status = message["status"]
                    current.set_attribute("http.response.status_code", status)
                    if status >= 500:
                        current.set_status(Status(StatusCode.ERROR))
                await send(message)
            try:
                await self.app(scope, receive, traced_send)
            finally:
                route = scope.get("route")
                if route is not None:
                    current.set_attribute("http.route", route.path)
