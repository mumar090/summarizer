import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import DocumentRepository
from app.db.session import get_session
from app.schemas.document_model import DocumentCreate, DocumentOut
from app.tasks.summarize import summarize_document

logger = logging.getLogger(__name__)

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/documents/", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    payload: DocumentCreate,
    response: Response,
    session: SessionDep,
):
    repo = DocumentRepository(session)
    doc = await repo.create(payload.name, str(payload.URL))
    # Commit BEFORE enqueueing: otherwise a fast worker can look the row up before it exists.
    await session.commit()

    try:
        summarize_document.delay(doc.document_uuid)
    except Exception:
        logger.exception("Failed to enqueue document %s", doc.document_uuid)
        await repo.mark_failed(doc, "Could not queue the summarization task; please retry.")
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue unavailable, please retry later",
        ) from None

    response.headers["Location"] = f"/api/documents/{doc.document_uuid}/"
    return doc


@router.get("/documents/{document_uuid}/", response_model=DocumentOut)
async def get_document(
    document_uuid: uuid.UUID,
    session: SessionDep,
):
    doc = await DocumentRepository(session).get(str(document_uuid))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc
