from celery import Celery

from app.core.config import settings

celery_app = Celery("summarizer", broker=settings.CELERY_BROKER_URL, include=["app.tasks.summarize"])

celery_app.conf.update(
    # Status and results are stored in the database, which the API already reads from,
    # so a Celery result backend would only duplicate state.
    task_ignore_result=True,
    # Acknowledge only after the task finishes: if a worker crashes mid-summary the message is
    # redelivered instead of lost. Tasks are idempotent (they skip finished documents).
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # LLM tasks are long; don't let one worker hoard queued messages.
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Fail fast when publishing so the API can answer 503 instead of hanging.
    task_publish_retry_policy={"max_retries": 2, "interval_start": 0, "interval_step": 0.5},
)
