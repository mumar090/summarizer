from celery.utils.log import get_task_logger
from sqlalchemy import update

from app.celery_app import celery_app
from app.core.config import settings
from app.core.errors import SummarizationError, TransientError
from app.db.models import TERMINAL_STATUSES, Document, StatusEnum
from app.db.session import SyncSessionLocal
from app.services.summarizer_service import summarize_url

logger = get_task_logger(__name__)


def _update(document_uuid: str, **values) -> None:
    with SyncSessionLocal.begin() as session:
        session.execute(update(Document).where(Document.document_uuid == document_uuid).values(**values))


def _fail(document_uuid: str, message: str) -> None:
    _update(document_uuid, status=StatusEnum.FAILED, error_message=message)


@celery_app.task(bind=True, name="summarize_document", max_retries=settings.TASK_MAX_RETRIES)
def summarize_document(self, document_uuid: str) -> None:
    """Fetch, extract and summarize a document, recording status and progress in the DB."""
    with SyncSessionLocal() as session:
        doc = session.get(Document, document_uuid)
        if doc is None:
            logger.warning("Document %s not found; skipping", document_uuid)
            return
        if doc.status in TERMINAL_STATUSES:
            # Redelivered message (acks_late) for a document that already finished.
            logger.info("Document %s already %s; skipping", document_uuid, doc.status.value)
            return
        url = doc.URL

    def on_progress(status: StatusEnum, progress: float) -> None:
        _update(document_uuid, status=status, data_progress=round(progress, 3))

    attempt = self.request.retries + 1
    try:
        summary = summarize_url(url, on_progress=on_progress)
    except TransientError as exc:
        if self.request.retries < self.max_retries:
            countdown = settings.TASK_RETRY_BASE_SECONDS * 2**self.request.retries
            logger.warning("Attempt %d for %s failed: %s", attempt, document_uuid, exc)
            _update(
                document_uuid,
                status=StatusEnum.PENDING,
                error_message=f"Attempt {attempt} failed: {exc}. Retrying in {countdown}s.",
            )
            raise self.retry(exc=exc, countdown=countdown) from exc
        _fail(document_uuid, f"Gave up after {attempt} attempts: {exc}")
        return
    except SummarizationError as exc:
        _fail(document_uuid, str(exc))
        return
    except Exception:
        logger.exception("Unexpected error summarizing %s", document_uuid)
        _fail(document_uuid, "Unexpected internal error while summarizing")
        return

    _update(
        document_uuid,
        status=StatusEnum.SUCCESS,
        summary=summary,
        data_progress=1.0,
        error_message=None,
    )
