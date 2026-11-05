
import logging
import time
from contextlib import contextmanager
from app.monitoring.tracing import span


logger = logging.getLogger("copilot.rag")


@contextmanager
def measure_stage(stage: str, request_id: str):
    start = time.perf_counter()

    try:
        with span("rag." + stage, **{"request.id": request_id}):
            yield
    finally:
        duration_ms = (
            time.perf_counter() - start
        ) * 1000

        logger.info(
            "rag_stage_complete "
            "request_id=%s stage=%s duration_ms=%.2f",
            request_id,
            stage,
            duration_ms,
        )
