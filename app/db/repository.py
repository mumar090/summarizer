from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.models import Document, StatusEnum


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


async def create(self, name: str, URL: str) -> Document:
    doc = Document(name=name, URL=URL)
    self.session.add(doc)
    await self.session.flush()
    await self.session.refresh(doc)
    return doc


async def get(self, document_uuid: str) -> Optional[Document]:
    q = select(Document).where(Document.document_uuid == document_uuid)
    res = await self.session.execute(q)
    return res.scalars().first()


async def update_status(self, document: Document, status: StatusEnum, **kwargs) -> Document:
    document.status = status
    if "summary" in kwargs:
        document.summary = kwargs.get("summary")
    if "data_progress" in kwargs:
        document.data_progress = kwargs.get("data_progress")
    if "error_message" in kwargs:
        document.error_message = kwargs.get("error_message")
    self.session.add(document)
    await self.session.flush()
    await self.session.refresh(document)
    return document


async def find_by_name_or_url(self, name: str, URL: str) -> Optional[Document]:
    q = select(Document).where((Document.name == name) | (Document.URL == URL))
    res = await self.session.execute(q)
    return res.scalars().first()