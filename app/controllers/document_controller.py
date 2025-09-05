from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.schemas.document_model import DocumentCreate, DocumentOut
from app.db.models import Document, StatusEnum
from app.db.session import get_session
from app.tasks.summarize import summarize_document

router = APIRouter()

@router.post("/documents/", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    payload: DocumentCreate,
    session: AsyncSession = Depends(get_session)
):
    doc = Document(name=payload.name, URL=str(payload.URL), status=StatusEnum.PENDING.value)
    session.add(doc)
    await session.flush()  # ensures doc gets UUID before commit

    summarize_document.delay(str(doc.document_uuid))  # send async task

    await session.refresh(doc)
    await session.commit()
    return doc


@router.get("/documents/{document_uuid}/", response_model=DocumentOut)
async def get_document(
    document_uuid: str,
    session: AsyncSession = Depends(get_session)
):
    result = await session.get(Document, document_uuid)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return result
