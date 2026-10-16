from fastapi import FastAPI

app = FastAPI(
    title="Enterprise AI Operations Copilot",
    version="0.1.0"
)

@app.get("/")
def root():
    return {"message": "Enterprise AI Copilot API"}

@app.get("/health")
def health():
    return {"status": "healthy"}