import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.controllers import document_controller
from app.core.config import settings
from app.db.session import async_engine, init_db

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="Summarizes web pages asynchronously using a local Ollama LLM and Celery workers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(document_controller.router, prefix="/api", tags=["documents"])


@app.get("/health", tags=["health"])
async def health():
    """Liveness: the process is up."""
    return {"status": "ok", "environment": settings.ENV}


@app.get("/ready", tags=["health"])
async def ready():
    """Readiness: the database is reachable."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}
