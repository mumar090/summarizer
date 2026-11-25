import os
import tempfile
from pathlib import Path

# Configure the app for tests BEFORE any app module is imported (settings are read at import).
_db_path = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path.as_posix()}"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["TASK_RETRY_BASE_SECONDS"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.db.models import Base, Document  # noqa: E402
from app.db.session import SyncSessionLocal, sync_engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # One client (and so one event loop) for the session, matching how uvicorn runs the app.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    Base.metadata.create_all(sync_engine)
    yield SyncSessionLocal
    with SyncSessionLocal.begin() as session:
        session.execute(delete(Document))


class FakeLLM:
    """Records prompts and returns canned output."""

    def __init__(self, reply="A short factual summary."):
        self.reply = reply
        self.prompts: list[str] = []

    def generate(self, prompt, *, system=None, max_tokens=512):
        self.prompts.append(prompt)
        return self.reply(prompt) if callable(self.reply) else self.reply


@pytest.fixture
def fake_llm():
    return FakeLLM()
