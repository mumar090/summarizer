import pytest
from celery.exceptions import Retry

from app.core.errors import SummarizationError, TransientError
from app.db.models import Document, StatusEnum
from app.tasks import summarize as task_module
from app.tasks.summarize import summarize_document


@pytest.fixture
def doc_id(db):
    with db.begin() as session:
        doc = Document(name="A", URL="https://example.com", status=StatusEnum.PENDING, data_progress=0.0)
        session.add(doc)
        session.flush()
        return doc.document_uuid


def _raise_transient(url, on_progress):
    raise TransientError("timeout")


def _load(db, doc_id) -> Document:
    with db() as session:
        return session.get(Document, doc_id)


def test_success_stores_summary_and_progress(db, doc_id, monkeypatch):
    def fake_summarize(url, on_progress):
        on_progress(StatusEnum.FETCHING, 0.05)
        on_progress(StatusEnum.SUMMARIZING, 0.5)
        return "The summary."

    monkeypatch.setattr(task_module, "summarize_url", fake_summarize)

    summarize_document.apply(args=[doc_id])

    doc = _load(db, doc_id)
    assert doc.status == StatusEnum.SUCCESS
    assert doc.summary == "The summary."
    assert doc.data_progress == 1.0
    assert doc.error_message is None


def test_permanent_error_fails_without_retry(db, doc_id, monkeypatch):
    def fail(url, on_progress):
        raise SummarizationError("Page returned HTTP 404")

    monkeypatch.setattr(task_module, "summarize_url", fail)

    summarize_document.apply(args=[doc_id])

    doc = _load(db, doc_id)
    assert doc.status == StatusEnum.FAILED
    assert doc.error_message == "Page returned HTTP 404"


def test_transient_error_schedules_retry(db, doc_id, monkeypatch):
    monkeypatch.setattr(task_module, "summarize_url", _raise_transient)
    retries = []

    def fake_retry(exc, countdown):
        retries.append(countdown)
        return Retry(exc=exc, when=countdown)

    monkeypatch.setattr(summarize_document, "retry", fake_retry)

    result = summarize_document.apply(args=[doc_id])

    assert isinstance(result.result, Retry)
    assert len(retries) == 1
    doc = _load(db, doc_id)
    assert doc.status == StatusEnum.PENDING
    assert "Retrying" in doc.error_message


def test_gives_up_after_max_retries(db, doc_id, monkeypatch):
    monkeypatch.setattr(task_module, "summarize_url", _raise_transient)

    summarize_document.apply(args=[doc_id], retries=summarize_document.max_retries)

    doc = _load(db, doc_id)
    assert doc.status == StatusEnum.FAILED
    assert doc.error_message.startswith("Gave up after")


def test_unexpected_error_does_not_leak_details(db, doc_id, monkeypatch):
    def boom(url, on_progress):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(task_module, "summarize_url", boom)

    summarize_document.apply(args=[doc_id])

    doc = _load(db, doc_id)
    assert doc.status == StatusEnum.FAILED
    assert "secret" not in doc.error_message


def test_redelivered_finished_document_is_skipped(db, doc_id, monkeypatch):
    with db.begin() as session:
        session.get(Document, doc_id).status = StatusEnum.SUCCESS
    called = []
    monkeypatch.setattr(task_module, "summarize_url", lambda url, on_progress: called.append(url))

    summarize_document.apply(args=[doc_id])

    assert called == []
