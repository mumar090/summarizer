from fastapi import FastAPI
from app.controllers import document_controller
from app.core.config import settings

app = FastAPI(
    title="Summarizer API",
    description="Summarizes documents/web pages using Ollama and Celery",
    version="0.1.0",
)

# Register routers
app.include_router(document_controller.router, prefix="/api", tags=["documents"])

# Health check / root endpoints
@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "Summarizer API is running"}

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy", "environment": settings.ENV}
