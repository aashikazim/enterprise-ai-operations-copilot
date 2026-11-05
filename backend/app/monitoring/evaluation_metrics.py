"""Safe, bounded-cardinality per-process enqueue aggregates.

No request IDs, customer IDs or content are metric labels. Export is added by
the monitoring milestone; counters reset when this process restarts.
"""
import logging
from collections import Counter
from threading import Lock
from time import perf_counter


logger = logging.getLogger("copilot.evaluation")
_lock = Lock()
_counts = Counter()
_duration_sum_ms = 0.0
OUTCOMES = frozenset({
    "disabled", "not_sampled", "abstained", "empty_evidence", "invalid_citations",
    "invalid_evidence", "enqueued", "enqueue_failed",
})


def record_enqueue(outcome, request_id, started):
    global _duration_sum_ms
    if outcome not in OUTCOMES:
        raise ValueError("Unknown enqueue outcome")
    elapsed = (perf_counter() - started) * 1000
    with _lock:
        _counts[outcome] += 1
        _duration_sum_ms += elapsed
    logger.info("rag_evaluation request_id=%s outcome=%s duration_ms=%.3f", request_id, outcome, elapsed)


def enqueue_snapshot():
    with _lock:
        return {"counts": dict(_counts), "duration_sum_ms": _duration_sum_ms}
