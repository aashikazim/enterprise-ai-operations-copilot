from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth.limiter import limiter

from app.api.customers import router as customers_router
from app.api.tickets import router as tickets_router
from app.auth.routes import router as auth_router
from app.auth.invitation_routes import (
    router as invitation_router,
)
from app.api.knowledge import router as knowledge_router
from app.api.rag import router as rag_router
from app.api.evaluation_jobs import router as evaluation_job_router
from app.api.monitoring import router as monitoring_router
from app.api.agents import router as agents_router
from app.api.conversations import router as conversations_router
from app.api.approvals import router as approvals_router
from app.api.connectors import router as connectors_router
from app.api.admin import router as admin_router
from app.monitoring.tracing import TracingMiddleware
from app.auth.http_security import SecurityMiddleware


app = FastAPI(
    title="Enterprise AI Operations Copilot",
    version="0.2.0"
)

app.state.limiter = limiter
app.add_middleware(TracingMiddleware)
app.add_middleware(SecurityMiddleware)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request, exc):
    # Pydantic's default input/context fields can echo passwords or document text.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(error["loc"]), "type": error["type"], "msg": "Invalid request value"}
        for error in exc.errors()
    ]})

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.include_router(customers_router)
app.include_router(tickets_router)
app.include_router(auth_router)
app.include_router(invitation_router)
app.include_router(knowledge_router)
app.include_router(rag_router)
app.include_router(evaluation_job_router)
app.include_router(monitoring_router)
app.include_router(agents_router)
app.include_router(conversations_router)
app.include_router(approvals_router)
app.include_router(connectors_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "Enterprise AI Copilot API"}

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    from sqlalchemy import text
    from app.db.database import SessionLocal
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}
