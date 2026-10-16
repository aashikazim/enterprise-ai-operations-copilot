from fastapi import FastAPI

from app.api.customers import router as customers_router
from app.api.tickets import router as tickets_router
from app.auth.routes import router as auth_router

app = FastAPI(
    title="Enterprise AI Operations Copilot",
    version="0.2.0"
)

app.include_router(customers_router)
app.include_router(tickets_router)
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "Enterprise AI Copilot API"}

@app.get("/health")
def health():
    return {"status": "healthy"}