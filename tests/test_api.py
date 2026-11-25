import uuid

from app.controllers import document_controller
from app.db.models import Document


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").status_code == 200


def test_create_document_commits_then_enqueues(client, db, monkeypatch):
    seen_in_db = []

    def fake_delay(document_uuid):
        # The row must already be committed when the task is queued (a worker could run now).
        with db() as session:
            seen_in_db.append(session.get(Document, document_uuid) is not None)

    monkeypatch.setattr(document_controller.summarize_document, "delay", fake_delay)

    resp = client.post("/api/documents/", json={"name": "Article", "URL": "https://example.com/a"})

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["data_progress"] == 0.0
    assert body["summary"] is None
    assert resp.headers["Location"] == f"/api/documents/{body['document_uuid']}/"
    assert seen_in_db == [True]


def test_get_document_round_trip(client, db, monkeypatch):
    monkeypatch.setattr(document_controller.summarize_document, "delay", lambda _id: None)
    created = client.post("/api/documents/", json={"name": "A", "URL": "https://example.com"}).json()

    resp = client.get(f"/api/documents/{created['document_uuid']}/")

    assert resp.status_code == 200
    assert resp.json()["name"] == "A"


def test_unknown_document_is_404(client, db):
    assert client.get(f"/api/documents/{uuid.uuid4()}/").status_code == 404


def test_malformed_uuid_is_422(client):
    assert client.get("/api/documents/not-a-uuid/").status_code == 422


def test_invalid_url_is_422(client):
    resp = client.post("/api/documents/", json={"name": "A", "URL": "not a url"})
    assert resp.status_code == 422


def test_queue_down_returns_503_and_marks_failed(client, db, monkeypatch):
    def broken_delay(_id):
        raise ConnectionError("redis down")

    monkeypatch.setattr(document_controller.summarize_document, "delay", broken_delay)

    resp = client.post("/api/documents/", json={"name": "A", "URL": "https://example.com"})

    assert resp.status_code == 503
    with db() as session:
        doc = session.query(Document).one()
        assert doc.status.value == "FAILED"
        assert "queue" in doc.error_message
