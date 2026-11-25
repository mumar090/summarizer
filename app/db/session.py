from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import create_engine, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Base


def _ensure_sqlite_dir(url: str) -> None:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.DATABASE_URL)

# Async engine: used by the FastAPI request handlers.
async_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

# Sync engine: used by Celery workers. Celery tasks are synchronous, and wrapping each one in
# asyncio.run() breaks pooled async connections that are bound to a previous event loop.
sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    # create_all is enough for a single-table service; use Alembic once the schema evolves.
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
