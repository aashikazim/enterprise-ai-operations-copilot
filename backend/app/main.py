from fastapi import FastAPI
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

app = FastAPI(
    title="Enterprise AI Operations Copilot",
    version="0.2.0"
)

app.state.limiter = limiter

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

@app.get("/")
def root():
    return {"message": "Enterprise AI Copilot API"}

@app.get("/health")
def health():
    return {"status": "healthy"}