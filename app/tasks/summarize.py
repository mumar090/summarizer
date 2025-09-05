import asyncio
from app.services.summarizer_service import summarize_url
from app.db.models import Document, StatusEnum
from app.db.session import AsyncSessionLocal
from worker import celery_app


@celery_app.task(name="summarize_document")
def summarize_document(document_uuid: str):
    """Celery task to fetch a document, summarize it, and update DB."""

    async def _run():
        async with AsyncSessionLocal() as session:
            doc = await session.get(Document, document_uuid)
            if not doc:
                return

            doc.status = StatusEnum.PROCESSING.value
            await session.commit()

            try:
                summary, _ = summarize_url(doc.URL)  # sync function call
                doc.summary = summary
                doc.status = StatusEnum.SUCCESS.value
            except Exception as e:
                doc.status = StatusEnum.FAILED.value
                doc.summary = f"Error: {str(e)}"
            finally:
                await session.commit()

    asyncio.run(_run())
